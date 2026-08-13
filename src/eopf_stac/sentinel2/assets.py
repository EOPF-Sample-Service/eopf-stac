import os
from copy import deepcopy

import numpy as np
import pystac
from pystac.extensions.eo import Band

from eopf_stac.common.constants import (
    DATASET_ASSET_EXTRA_FIELDS,
    MEDIA_TYPE_ZARR,
    PRODUCT_ASSET_KEY,
    PRODUCT_METADATA_ASSET_KEY,
    PRODUCT_METADATA_PATH,
    RASTER_EXTENSION_SCHEMA_URI,
    ROLE_DATA,
    ROLE_DATASET,
    ZIPPED_PRODUCT_ASSET_KEY,
    get_item_asset_metadata,
    get_item_asset_product,
)
from eopf_stac.common.stac import create_zipped_product_asset
from eopf_stac.sentinel2.constants import (
    ASSET_TO_DESCRIPTION,
    DATASET_PATHS_TO_ASSET,
    L2A_AOT_WVP_ASSETS_TO_PATH,
    L2A_SCL_ASSETS_TO_PATH,
    ROLE_REFLECTANCE,
    SENTINEL2_BANDS_DICT,
    SENTINEL2_BANDS_TO_ASSET_NAME,
)


def get_band_item_assets(band_asset_defs: dict) -> dict[str, pystac.ItemAssetDefinition]:
    item_assets = {}
    for key in band_asset_defs.keys():
        band_key = band_key_from_asset_key(key)
        item_assets[key] = create_item_asset(
            asset_key=key,
            roles=[ROLE_DATA, ROLE_REFLECTANCE],
            band_keys=[band_key],
        )
    return item_assets


def get_band_assets(
    band_asset_defs: dict, asset_href: str, metadata: dict, item: pystac.Item
) -> dict[str, pystac.Asset]:
    assets = {}
    item_assets = get_band_item_assets(band_asset_defs)
    for key, item_asset in item_assets.items():
        href_suffix = band_asset_defs[key]
        asset = item_asset.create_asset(os.path.join(asset_href, href_suffix))

        attrs = metadata.get(f"{href_suffix}/.zattrs")
        if attrs:
            update_extra_fields_from_metadata(asset=asset, attrs=attrs, item=item)

        assets[key] = asset

    return assets


def get_aot_wvp_item_assets() -> dict[str, pystac.ItemAssetDefinition]:
    item_assets = {}
    for key in L2A_AOT_WVP_ASSETS_TO_PATH.keys():
        item_asset = create_item_asset(
            asset_key=key,
            roles=[ROLE_DATA],
            band_keys=[],
            extra_fields={},
            title_with_resolution=False,
        )
        item_assets[key] = item_asset
    return item_assets


def get_aot_wvp_assets(
    aot_wvp_asset_defs: dict, asset_href: str, metadata: dict, item: pystac.Item
) -> dict[str, pystac.Asset]:
    assets = {}
    item_assets = get_aot_wvp_item_assets()
    for key, item_asset in item_assets.items():
        href_suffix = aot_wvp_asset_defs[key]
        asset = item_asset.create_asset(os.path.join(asset_href, href_suffix))

        attrs = metadata.get(f"{href_suffix}/.zattrs")
        if attrs:
            update_extra_fields_from_metadata(asset=asset, attrs=attrs, item=item)

        assets[key] = asset

    # data_type
    # nodata
    # raster:scale
    # raster:offset

    return assets


def get_scl_item_assets() -> dict[str, pystac.ItemAssetDefinition]:
    item_assets = {}
    for key in L2A_SCL_ASSETS_TO_PATH.keys():
        item_assets[key] = create_item_asset(
            asset_key=key,
            roles=[ROLE_DATA],
            band_keys=[],
            extra_fields={},
            title_with_resolution=False,
        )
    return item_assets


def get_scl_assets(scl_asset_defs: dict, asset_href: str, metadata: dict, item: pystac.Item) -> dict[str, pystac.Asset]:
    assets = {}
    item_assets = get_scl_item_assets()
    for key, item_asset in item_assets.items():
        href_suffix = scl_asset_defs[key]
        # SCL can be opened as zarr group / xarray dataset -> remove the 'scl' part of the path
        # asset = item_asset.create_asset(os.path.dirname(os.path.join(asset_href, href_suffix)))
        asset = item_asset.create_asset(os.path.join(asset_href, href_suffix))

        attrs = metadata.get(f"{href_suffix}/.zattrs")
        if attrs:
            update_extra_fields_from_metadata(asset=asset, attrs=attrs, item=item)

        assets[key] = asset

    # classification:classes
    # nodata
    # data_type

    return assets


def get_tci_item_assets(tci_asset_defs: dict) -> dict[str, pystac.ItemAssetDefinition]:
    item_assets = {}
    for key in tci_asset_defs.keys():
        item_assets[key] = create_item_asset(
            asset_key=key,
            roles=[ROLE_DATA],
            band_keys=["B04", "B03", "B02"],
            extra_fields={},
            title_with_resolution=False,
        )
    return item_assets


def get_tci_assets(tci_asset_defs: dict, asset_href: str, metadata: dict, item: pystac.Item) -> dict[str, pystac.Asset]:
    assets = {}
    item_assets = get_tci_item_assets(tci_asset_defs)
    for key, item_asset in item_assets.items():
        href_suffix = tci_asset_defs[key]
        asset = item_asset.create_asset(os.path.join(asset_href, href_suffix))

        attrs = metadata.get(f"{href_suffix}/.zattrs")
        if attrs:
            update_extra_fields_from_metadata(asset=asset, attrs=attrs, item=item)

        assets[key] = asset

    # nodata
    # data_type

    return assets


def get_dataset_item_assets() -> dict[str, pystac.ItemAssetDefinition]:
    item_assets = {}
    for key in DATASET_PATHS_TO_ASSET.keys():
        band_keys = []
        if key == "SR_10m":
            band_keys = ["B02", "B03", "B04", "B08"]
        elif key == "SR_20m":
            band_keys = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B8A", "B11", "B12"]
        elif key == "SR_60m":
            band_keys = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B8A", "B09", "B11", "B12"]

        item_assets[key] = create_item_asset(
            asset_key=key,
            roles=[ROLE_DATA, ROLE_REFLECTANCE, ROLE_DATASET],
            band_keys=band_keys,
            extra_fields=deepcopy(DATASET_ASSET_EXTRA_FIELDS),
        )
    return item_assets


def get_dataset_assets(
    dataset_asset_defs: dict, asset_href: str, metadata: dict, item: pystac.Item
) -> dict[str, pystac.Asset]:
    assets = {}
    item_assets = get_dataset_item_assets()
    for key, item_asset in item_assets.items():
        href_suffix = dataset_asset_defs[key]
        asset = item_asset.create_asset(os.path.join(asset_href, href_suffix))

        attrs = metadata.get(f"{href_suffix}/.zattrs")
        if attrs:
            update_extra_fields_from_metadata(asset=asset, attrs=attrs, item=item)

        assets[key] = asset

    # nodata
    # data_type

    return assets


def get_extra_assets(asset_href: str, item: pystac.Item, collection_id: str) -> dict[str, pystac.Asset]:
    metadata = get_item_asset_metadata().create_asset(os.path.join(asset_href, PRODUCT_METADATA_PATH))
    product = get_item_asset_product().create_asset(asset_href)
    zip_product = create_zipped_product_asset(eopf_href=asset_href, collection_id=collection_id, item_id=item.id)
    metadata.set_owner(item)
    product.set_owner(item)
    zip_product.set_owner(item)
    return {PRODUCT_METADATA_ASSET_KEY: metadata, PRODUCT_ASSET_KEY: product, ZIPPED_PRODUCT_ASSET_KEY: zip_product}


def create_item_asset(
    asset_key: str,
    roles: list[str],
    band_keys: list[str] = [],
    extra_fields: dict = {},
    title_with_resolution: bool = True,
) -> pystac.ItemAssetDefinition:
    gsd = unsuffixed_band_resolution(asset_key)
    band_key = band_key_from_asset_key(asset_key)
    extra_fields["gsd"] = int(gsd)

    if len(band_keys) > 0:
        bands = get_bands_for_band_keys(band_keys)
        extra_fields["bands"] = bands

    title = ASSET_TO_DESCRIPTION[band_key]
    if title_with_resolution:
        title = f"{title} - {gsd}m"

    return pystac.ItemAssetDefinition.create(
        title=title,
        description=None,
        media_type=MEDIA_TYPE_ZARR,
        roles=roles,
        extra_fields=extra_fields,
    )


def get_bands_for_band_keys(keys: list[str]) -> list[Band]:
    bands = []
    for band_key in keys:
        band = SENTINEL2_BANDS_DICT[SENTINEL2_BANDS_TO_ASSET_NAME[band_key]]
        band["description"] = f"{ASSET_TO_DESCRIPTION[band_key]}"
        bands.append(band)
    return bands


def band_key_from_asset_key(asset_key: str) -> str:
    # asset_key e.g. B02_10m
    parts = asset_key.split("_")
    return parts[0]


def unsuffixed_band_resolution(asset_key: str) -> str:
    # asset_key e.g. B02_10m
    parts = asset_key.split("_")
    return parts[1][:2]


def update_extra_fields_from_metadata(asset: pystac.Asset, attrs: dict, item: pystac.Item):
    attrs = attrs.get("_eopf_attrs")

    if attrs.get("long_name"):
        asset.description = attrs.get("long_name")

    if attrs.get("proj:bbox"):
        asset.extra_fields["proj:bbox"] = attrs.get("proj:bbox")

    if attrs.get("proj:shape"):
        asset.extra_fields["proj:shape"] = attrs.get("proj:shape")

    if attrs.get("proj:transform"):
        asset.extra_fields["proj:transform"] = attrs.get("proj:transform")

    if attrs.get("proj:epsg"):
        asset.extra_fields["proj:code"] = f"EPSG:{attrs.get('proj:epsg')}"

    scale = attrs.get("scale_factor")
    offset = attrs.get("add_offset")
    if any([scale, offset]):
        if RASTER_EXTENSION_SCHEMA_URI not in item.stac_extensions:
            item.stac_extensions.append(RASTER_EXTENSION_SCHEMA_URI)
        if scale is not None:
            asset.extra_fields["raster:scale"] = scale
        if offset is not None:
            asset.extra_fields["raster:offset"] = offset

    if attrs.get("fill_value") is not None:
        asset.extra_fields["nodata"] = attrs.get("fill_value")

    if attrs.get("dtype") is not None:
        asset.extra_fields["data_type"] = str(np.dtype(attrs.get("dtype")))
