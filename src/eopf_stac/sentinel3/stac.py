import logging
import os
from copy import deepcopy

import pystac
from pystac.extensions.sat import SatExtension

from eopf_stac.common.constants import (
    EO_EXTENSION_SCHEMA_URI,
    PROCESSING_EXTENSION_SCHEMA_URI,
    PRODUCT_EXTENSION_SCHEMA_URI,
    SENTINEL_LICENSE,
    SUPPORTED_S3_OLCI_L1_PRODUCT_TYPES,
    SUPPORTED_S3_OLCI_L2_PRODUCT_TYPES,
    SUPPORTED_S3_SLSTR_L1_PRODUCT_TYPES,
    SUPPORTED_S3_SLSTR_L2_FRP_PRODUCT_TYPE,
    SUPPORTED_S3_SLSTR_L2_LST_PRODUCT_TYPE,
    THUMBNAIL_ASSET,
    ZIPPED_PRODUCT_ASSET_KEY,
)
from eopf_stac.common.stac import (
    create_cdse_link,
    create_zipped_product_asset,
    fill_eo_properties,
    fill_eopf_properties,
    fill_processing_properties,
    fill_product_properties,
    fill_sat_properties,
    fill_timestamp_properties,
    fill_version_properties,
    fix_geometry,
    get_datetimes,
    get_identifier_from_href,
    is_valid_string,
    rearrange_bbox,
)
from eopf_stac.sentinel3.constants import (
    OLCI_L1_ASSETS,
    OLCI_L1_ASSETS_KEY_TO_PATH,
    OLCI_L2_ASSETS,
    OLCI_L2_ASSETS_KEY_TO_PATH,
    SENTINEL3_METADATA,
    SLSTR_L1_ASSETS,
    SLSTR_L1_ASSETS_KEY_TO_PATH,
    SLSTR_L2_FRP_ASSETS,
    SLSTR_L2_FRP_ASSETS_KEY_TO_PATH,
    SLSTR_L2_LST_ASSETS,
    SLSTR_L2_LST_ASSETS_KEY_TO_PATH,
)

logger = logging.getLogger(__name__)


def create_collection(collection_metadata: dict, thumbnail_href: str) -> pystac.Collection:
    mission_metadata = SENTINEL3_METADATA
    summary_dict = {
        "constellation": [mission_metadata.get("constellation")],
        "platform": mission_metadata.get("platforms"),
        "instruments": collection_metadata.get("instruments"),
        "gsd": collection_metadata.get("gsd"),
        "processing:level": [collection_metadata.get("processing_level")],
        "product:type": [collection_metadata.get("product_type")],
    }

    collection = pystac.Collection(
        id=collection_metadata.get("id"),
        description=collection_metadata.get("description"),
        extent=mission_metadata.get("extent"),
        title=collection_metadata.get("title"),
        providers=mission_metadata.get("providers"),
        keywords=mission_metadata.get("keywords"),
        stac_extensions=[
            SatExtension.get_schema_uri(),
            PRODUCT_EXTENSION_SCHEMA_URI,
            PROCESSING_EXTENSION_SCHEMA_URI,
            EO_EXTENSION_SCHEMA_URI,
        ],
        summaries=pystac.Summaries(summary_dict),
    )
    collection.links.append(SENTINEL_LICENSE)

    # -- Assets
    thumbnail_asset = deepcopy(THUMBNAIL_ASSET)
    thumbnail_asset.title = f"{collection.title} thumbnail"
    thumbnail_asset.href = os.path.join(thumbnail_href, f"{collection.id}.png")
    collection.add_asset("thumbnail", thumbnail_asset)

    # -- Item Assets
    collection.item_assets = collection_metadata.get("item_assets")

    # -- Summaries
    sat = SatExtension.summaries(collection, add_if_missing=True)
    sat.orbit_state = mission_metadata["sat"]["orbit_state"]
    sat.platform_international_designator = mission_metadata["sat"]["platform_international_designator"]

    return collection


def create_item(
    metadata: dict,
    product_type: str,
    asset_href_prefix: str,
    cpm_version: str = None,
    cdse_scene_id: str | None = None,
    cdse_scene_href: str | None = None,
    collection_id: str | None = None,
) -> pystac.Item:
    stac_discovery = metadata[".zattrs"]["stac_discovery"]
    # other_metadata = metadata[".zattrs"]["other_metadata"]
    properties = stac_discovery["properties"]

    # -- datetimes
    datetimes = get_datetimes(properties)
    datetime = datetimes[0]
    start_datetime = datetimes[1]
    end_datetime = datetimes[2]

    item = pystac.Item(
        id=get_identifier_from_href(asset_href_prefix),
        bbox=rearrange_bbox(stac_discovery.get("bbox")),
        geometry=stac_discovery.get("geometry"),
        properties={},
        datetime=datetime,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
    )

    # -- Geometry (fix antimeridian, unclosed ring, etc)
    fix_geometry(item)

    # -- Common metadata

    item.common_metadata.mission = SENTINEL3_METADATA["constellation"].capitalize()
    item.common_metadata.providers = SENTINEL3_METADATA["providers"]
    item.common_metadata.constellation = SENTINEL3_METADATA["constellation"]

    if properties.get("instruments"):
        item.common_metadata.instruments = properties.get("instruments")

    if properties.get("platform"):
        item.common_metadata.platform = properties.get("platform")

    gsd = properties.get("gsd")
    if gsd is not None:
        # CPM workaround: "gsd": 270
        if gsd == 270:
            gsd = 300
        item.common_metadata.gsd = gsd

    # -- Extensions

    # Timestamps
    fill_timestamp_properties(item, properties)

    # Satellite
    fill_sat_properties(item, properties)

    # Electro-Optical
    fill_eo_properties(item, properties)

    # Processing Extension
    baseline_version = None
    if properties.get("processing:software") is not None:
        baseline_version = properties.get("processing:software").get("PUG")
    fill_processing_properties(item, properties, cpm_version, baseline_version)

    # Product Extension
    fill_product_properties(item, product_type, properties)

    # EOPF Extension
    fill_eopf_properties(item, properties)

    # Version Extension
    fill_version_properties(item)

    # -- Assets

    logger.debug("Creating assets ...")

    assets = {}
    if product_type in SUPPORTED_S3_OLCI_L1_PRODUCT_TYPES:
        asset_defintions = OLCI_L1_ASSETS
        asset_path_lookups = OLCI_L1_ASSETS_KEY_TO_PATH
    elif product_type in SUPPORTED_S3_OLCI_L2_PRODUCT_TYPES:
        asset_defintions = OLCI_L2_ASSETS
        asset_path_lookups = OLCI_L2_ASSETS_KEY_TO_PATH
    elif product_type in SUPPORTED_S3_SLSTR_L1_PRODUCT_TYPES:
        asset_defintions = SLSTR_L1_ASSETS
        asset_path_lookups = SLSTR_L1_ASSETS_KEY_TO_PATH
    elif product_type in SUPPORTED_S3_SLSTR_L2_LST_PRODUCT_TYPE:
        asset_defintions = SLSTR_L2_LST_ASSETS
        asset_path_lookups = SLSTR_L2_LST_ASSETS_KEY_TO_PATH
    elif product_type in SUPPORTED_S3_SLSTR_L2_FRP_PRODUCT_TYPE:
        asset_defintions = SLSTR_L2_FRP_ASSETS
        asset_path_lookups = SLSTR_L2_FRP_ASSETS_KEY_TO_PATH
    else:
        raise ValueError(f"Unsupported Sentinel-3 product type '{product_type}'")

    for asset_key, item_asset in asset_defintions.items():
        if asset_key == ZIPPED_PRODUCT_ASSET_KEY:
            asset = create_zipped_product_asset(eopf_href=asset_href_prefix, collection_id=collection_id, item_id=item.id)
        else:
            path = asset_path_lookups[asset_key]
            if is_valid_string(path):
                asset = item_asset.create_asset(os.path.join(asset_href_prefix, path))
            else:
                asset = item_asset.create_asset(asset_href_prefix)
        assets[asset_key] = asset

    for key, asset in assets.items():
        assert key not in item.assets
        item.add_asset(key, asset)

    # -- Links
    item.links.append(SENTINEL_LICENSE)
    if cdse_scene_href is not None:
        item.links.append(create_cdse_link(cdse_scene_href))

    return item
