import json
import logging
import re

import pystac
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pystac.utils import datetime_to_str, now_in_utc

from eopf_stac.common.constants import (
    PRODUCT_TYPE_TO_COLLECTION,
    S2_MGRS_PATTERN,
)
from eopf_stac.common.stac import (
    fix_geometry,
    get_identifier_from_href,
    get_zipped_zarr_store_url,
    rearrange_bbox,
)

logger = logging.getLogger(__name__)


class StacItemBuilderS2:
    def __init__(self, product_type: str):
        self.product_type = product_type

    def build(self, metadata: dict, url: str, cdse_stac_item_url: str | None) -> pystac.Item:
        # Derive extra information
        identifier = get_identifier_from_href(product_href=url)
        mgrs_grid_data = self.get_mgrs_grid_properties(identifier)
        baseline_version = self.get_baseline_processing_version(identifier)

        # Determine URL for zipped product asset
        collection = PRODUCT_TYPE_TO_COLLECTION[self.product_type]
        zipped_zarr_store_href = get_zipped_zarr_store_url(url, collection, identifier)

        derived_data = {
            "id": identifier,
            "created": datetime_to_str(now_in_utc()),
            "grid:code": mgrs_grid_data["grid:code"],
            "mgrs:grid_square": mgrs_grid_data["mgrs:grid_square"],
            "mgrs:latitude_band": mgrs_grid_data["mgrs:latitude_band"],
            "mgrs:utm_zone": mgrs_grid_data["mgrs:utm_zone"],
            "processing:version": baseline_version,
            "zarr_store_href": url,
            "zarr_store_zipped_href": zipped_zarr_store_href,
            "cdse_item_uri": cdse_stac_item_url,
        }

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
        rendered = template.render(zarr=metadata, extra=derived_data)

        # Fails if JSON syntax is invalid
        data = json.loads(rendered)

        # Fails if JSON does not represent valid STAC item
        item = pystac.Item.from_dict(data)

        # Apply some geometry corrections
        fix_geometry(item)
        item.bbox = rearrange_bbox(item.bbox)

        # Validate item
        logger.debug(json.dumps(item.to_dict(), indent=2))
        item.validate()

        return item

    def get_baseline_processing_version(self, identifier: str) -> str | None:
        # S2B_MSIL1C_20240428T102559_N0510_R108_T32UPC_20240428T123125
        # S2A_MSIL2A_20250109T100401_N0511_R122_T34UCE_20250109T122750
        proc_version = None
        if identifier is not None:
            proc_version_pattern = re.compile(r"_N(\d{2})(\d{2})")
            proc_version_match = proc_version_pattern.search(identifier)
            if proc_version_match and len(proc_version_groups := proc_version_match.groups()) == 2:
                proc_version = f"{proc_version_groups[0]}.{proc_version_groups[1]}"

        return proc_version

    def get_mgrs_grid_properties(self, identifier: str) -> dict:
        data = {}
        if identifier is not None:
            mgrs_match = S2_MGRS_PATTERN.search(identifier)
            success = mgrs_match and len(mgrs_groups := mgrs_match.groups())
            if success:
                data["mgrs:grid_square"] = mgrs_groups[2]
                data["mgrs:latitude_band"] = mgrs_groups[1]
                data["mgrs:utm_zone"] = int(mgrs_groups[0])
                data["grid:code"] = (
                    f"MGRS-{data['mgrs:utm_zone']}{data['mgrs:latitude_band']}{data['mgrs:grid_square']}"
                )
        return data
