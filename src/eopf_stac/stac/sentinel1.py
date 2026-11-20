import json
import logging
import os

import pystac
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pystac.utils import datetime_to_str, now_in_utc
from shapely.geometry import shape

from eopf_stac.common.constants import (
    PRODUCT_TYPE_TO_COLLECTION,
)
from eopf_stac.common.stac import fix_geometry, get_identifier_from_href, get_zipped_zarr_store_url
from eopf_stac.common.version import get_eopf_stac_version
from eopf_stac.zarr.reader import ZarrMetadataReaderV3

logger = logging.getLogger(__name__)


def render_stac_item(template_file: str, zarr_metadata: dict, extra_metadata: dict) -> str:
    # StrictUndefined: Fails if required field is absent
    env = Environment(
        loader=FileSystemLoader("src/eopf_stac/stac/templates/"),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    template = env.get_template(template_file)
    rendered = template.render(zarr=zarr_metadata, extra=extra_metadata)
    return rendered


def check_validate_stac_item(rendered: str) -> pystac.Item:
    # Fails if JSON syntax is invalid
    data = json.loads(rendered)

    # Fails if JSON does not represent valid STAC item
    item = pystac.Item.from_dict(data)

    # Apply some geometry corrections
    fix_geometry(item)
    geom = shape(item.geometry)
    item.bbox = geom.bounds

    # Validate item
    logger.debug(json.dumps(item.to_dict(), indent=2))
    item.validate()

    return item


class StacItemBuilderS1GRD:
    def __init__(self, product_type: str):
        self.product_type = product_type

    def build(self, metadata: dict, url: str, cdse_stac_item_url: str | None) -> pystac.Item:
        collection = PRODUCT_TYPE_TO_COLLECTION[self.product_type]
        identifier = get_identifier_from_href(url)
        zipped_zarr_store_href = get_zipped_zarr_store_url(url, collection, identifier)

        # Read zarr.json in scene's root
        scene_id = metadata["attributes"]["stac_discovery"]["assets"]["grd"]["href"].split("/")[1]
        scene_url = os.path.join(url, scene_id)
        print(f"Reading GRD scene metadata from {scene_url}")
        reader = ZarrMetadataReaderV3()
        scene_metadata, _ = reader.read(scene_url)

        processing_software = metadata["attributes"]["stac_discovery"]["properties"]["processing:software"]
        processing_software["eopf-stac"] = get_eopf_stac_version()
        sar_beam_ids = metadata["attributes"]["stac_discovery"]["properties"]["sar:beam_ids"]
        sar_center_frequency = scene_metadata["attributes"]["stac_discovery"]["properties"]["sar:center_frequency"]
        sar_pixel_spacing_range = scene_metadata["attributes"]["stac_discovery"]["properties"][
            "sar:pixel_spacing_range"
        ]
        sar_pixel_spacing_azimuth = scene_metadata["attributes"]["stac_discovery"]["properties"][
            "sar:pixel_spacing_azimuth"
        ]
        view_incidence_angle = scene_metadata["attributes"]["stac_discovery"]["properties"]["view:incidence_angle"]

        derived_data = {
            "id": identifier,
            "created": datetime_to_str(now_in_utc()),
            "zarr_store_href": url,
            "zarr_store_zipped_href": zipped_zarr_store_href,
            "scene_zarr_store_href": scene_url,
            "processing:software": processing_software,
            "processing:version": metadata["attributes"]["stac_discovery"]["properties"]["processing:software"][
                "Sentinel-1 IPF"
            ],
            "eopf:instrument_mode": scene_metadata["attributes"]["stac_discovery"]["properties"][
                "eopf:instrument_mode"
            ],
            "sar:beam_ids": [sar_beam_ids],
            "sar:center_frequency": sar_center_frequency,
            "sar:pixel_spacing_range": sar_pixel_spacing_range,
            "sar:pixel_spacing_azimuth": sar_pixel_spacing_azimuth,
            "view:incidence_angle": view_incidence_angle,
        }

        # Render STAC item JSON from template
        template_file_path = f"{self.product_type}.json.j2"
        rendered = render_stac_item(
            template_file=template_file_path, zarr_metadata=metadata, extra_metadata=derived_data
        )

        # Check and validate rendered STAC item
        item = check_validate_stac_item(rendered)

        return item


class StacItemBuilderS1SLC:
    def __init__(self, product_type: str):
        self.product_type = product_type

    def build(self, metadata: dict, url: str, cdse_stac_item_url: str | None) -> pystac.Item:
        collection = PRODUCT_TYPE_TO_COLLECTION[self.product_type]
        zipped_zarr_store_href = get_zipped_zarr_store_url(url, collection, get_identifier_from_href(url))

        bursts = {}
        for key in metadata["consolidated_metadata"]["metadata"]:
            k = key.split("/")[0]
            if k not in bursts:
                # S01SIWSLC_20250819T045501_0030_A346_B9C4_0789BF_IW1_327474
                parts = k.split("_")
                swath = parts[6]
                burst_id = int(parts[7])
                burst_zarr_store_url = os.path.join(url, k)
                processing_software = metadata["attributes"]["stac_discovery"]["properties"]["processing:software"]
                processing_software["eopf-stac"] = get_eopf_stac_version()
                identifier = get_identifier_from_href(burst_zarr_store_url)
                zipped_burst_zarr_store_url = get_zipped_zarr_store_url(burst_zarr_store_url, collection, identifier)

                bursts[k] = {
                    "id": identifier,
                    "created": datetime_to_str(now_in_utc()),
                    "burst_zarr_group_href": burst_zarr_store_url,
                    "burst_zarr_group_zipped_href": zipped_burst_zarr_store_url,
                    "zarr_store_href": url,
                    "zarr_store_zipped_href": zipped_zarr_store_href,
                    "cdse_item_uri": None,
                    "processing_software": processing_software,
                    "processing:version": metadata["attributes"]["stac_discovery"]["properties"]["processing:software"][
                        "Sentinel-1 IPF"
                    ],
                    "swath": [swath],
                    "burst_id": burst_id,
                }
        print(f"{len(bursts)} bursts found")

        items = []
        for name, derived_data in bursts.items():
            burst_zarr_metadata = metadata["consolidated_metadata"]["metadata"][name]

            # Render STAC item JSON from template
            template_file_path = f"{self.product_type}.json.j2"
            rendered = render_stac_item(
                template_file=template_file_path, zarr_metadata=burst_zarr_metadata, extra_metadata=derived_data
            )

            # Check and validate rendered STAC item
            item = check_validate_stac_item(rendered)

            items.append(item)

        return items
