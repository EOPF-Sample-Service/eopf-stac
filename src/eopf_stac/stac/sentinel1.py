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

logger = logging.getLogger(__name__)


class StacItemBuilderS1:
    def __init__(self, product_type: str):
        self.product_type = product_type

    def build(self, metadata: dict, url: str, cdse_stac_item_url: str | None) -> pystac.Item:
        collection = PRODUCT_TYPE_TO_COLLECTION[self.product_type]
        zipped_zarr_store_href = get_zipped_zarr_store_url(url, collection, get_identifier_from_href(url))

        bursts = {}
        for key in metadata["consolidated_metadata"]["metadata"].keys():
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
            # StrictUndefined: Fails if required field is absent
            template_file_path = f"{self.product_type}.json.j2"
            env = Environment(
                loader=FileSystemLoader("src/eopf_stac/stac/templates/"),
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True,
                undefined=StrictUndefined,
            )
            template = env.get_template(template_file_path)
            rendered = template.render(zarr=burst_zarr_metadata, extra=derived_data)

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

            items.append(item)

        return items
