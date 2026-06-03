import re
from copy import deepcopy
from typing import Final

import pystac
from pystac.item_assets import ItemAssetDefinition
from pystac.link import Link
from pystac.provider import ProviderRole

from eopf_stac.common.eopf_xarray import EopfXarrayBackendConfig, OpMode

CDSE_STAC_API_URL = "https://stac.dataspace.copernicus.eu/v1"

SUPPORTED_PRODUCT_TYPES_S1 = [
    "S01SIWGRH",
    "S01SSMGRH",
    "S01SEWGRH",
    "S01SIWGRD",
    "S01SSMGRD",
    "S01SEWGRD",
    "S01SIWSLC",
    "S01SIVSLC",  # CPM workaround
    "S01SWVSLC",
    "S01SSMSLC",
    "S01SEWSLC",
    "S01SIWOCN",
    "S01SEWOCN",
    "S01SSMOCN",
    "S01SWVOCN",
]
SUPPORTED_PRODUCT_TYPES_S2 = ["S02MSIL1C", "S02MSIL2A"]

SUPPORTED_S3_OLCI_L1_PRODUCT_TYPES = ["S03OLCEFR", "S03OLCERR"]
SUPPORTED_S3_OLCI_L2_PRODUCT_TYPES = ["S03OLCLFR", "S03OLCLRR"]
SUPPORTED_S3_SLSTR_L1_PRODUCT_TYPES = ["S03SLSRBT"]
SUPPORTED_S3_SLSTR_L2_LST_PRODUCT_TYPE = ["S03SLSLST"]
SUPPORTED_S3_SLSTR_L2_FRP_PRODUCT_TYPE = ["S03SLSFRP"]
SUPPORTED_S3_SYN_L2_PRODUCT_TYPES = [
    "S03SYNSDR",
    "S03SYNVGP",
    "S03SYNVG1",
    "S03SYNV10",
    "S03SYNAOD",
]
SUPPORTED_PRODUCT_TYPES_S3 = (
    SUPPORTED_S3_OLCI_L1_PRODUCT_TYPES
    + SUPPORTED_S3_OLCI_L2_PRODUCT_TYPES
    + SUPPORTED_S3_SLSTR_L1_PRODUCT_TYPES
    + SUPPORTED_S3_SLSTR_L2_LST_PRODUCT_TYPE
    + SUPPORTED_S3_SLSTR_L2_FRP_PRODUCT_TYPE
    + SUPPORTED_S3_SYN_L2_PRODUCT_TYPES
)


# SUPPORTED_S3_SRAL_L1_PRODUCT_TYPES = ["S03AHRL1B"]  # sentinel-3-sra-l1b
# SUPPORTED_S3_SRAL_L2_PRODUCT_TYPES = ["S03AHRL2H"]  # sentinel-3-sra-l2-lan-hy
# other SRAL listed: S03AHRL1A (SR_1_SRA_A_), S03ALRL1A (SR_1_SRA_A_), S03ALRL1B (SR_1_SRA_BS), S03ALRL2H (SR_2_LAN_HY)
# [1] https://cpm.pages.eopf.copernicus.eu/eopf-cpm/main/PSFD/3-product-types-naming-rules.html

PRODUCT_TYPE_TO_COLLECTION: Final[dict] = {
    "S01SIWGRH": "sentinel-1-l1-grd",
    "S01SSMGRH": "sentinel-1-l1-grd",
    "S01SEWGRH": "sentinel-1-l1-grd",
    "S01SEWGRD": "sentinel-1-l1-grd",
    "S01SIWGRD": "sentinel-1-l1-grd",
    "S01SSMGRD": "sentinel-1-l1-grd",
    "S01SIWSLC": "sentinel-1-l1-slc",
    "S01SIVSLC": "sentinel-1-l1-slc",  # CPM workaround
    "S01SWVSLC": "sentinel-1-l1-slc",
    "S01SSMSLC": "sentinel-1-l1-slc",
    "S01SEWSLC": "sentinel-1-l1-slc",
    "S01SIWOCN": "sentinel-1-l2-ocn",
    "S01SEWOCN": "sentinel-1-l2-ocn",
    "S01SSMOCN": "sentinel-1-l2-ocn",
    "S01SWVOCN": "sentinel-1-l2-ocn",
    "S02MSIL1C": "sentinel-2-l1c",
    "S02MSIL2A": "sentinel-2-l2a",
    "S03OLCEFR": "sentinel-3-olci-l1-efr",
    "S03OLCERR": "sentinel-3-olci-l1-err",
    "S03OLCLFR": "sentinel-3-olci-l2-lfr",
    "S03OLCLRR": "sentinel-3-olci-l2-lrr",
    "S03SLSRBT": "sentinel-3-slstr-l1-rbt",
    "S03SLSFRP": "sentinel-3-slstr-l2-frp",
    "S03SLSLST": "sentinel-3-slstr-l2-lst",
    "S03SYNSDR": "sentinel-3-syn-l2",
    "S03SYNVGP": "sentinel-3-syn-l2-vgp",
    "S03SYNVG1": "sentinel-3-syn-l2-vg1",
    "S03SYNV10": "sentinel-3-syn-l2-v10",
    "S03SYNAOD": "sentinel-3-syn-l2-aod",
}

MEDIA_TYPE_ZARR = "application/vnd+zarr"
MEDIA_TYPE_JSON = "application/json"
MEDIA_TYPE_ZIP = "application/zip"

ROLE_DATA = "data"
ROLE_METADATA = "metadata"
ROLE_VISUAL = "visual"
ROLE_DATASET = "dataset"
ROLE_ARCHIVE = "archive"

SENTINEL_LICENSE: Final[Link] = Link(
    rel="license",
    title="Legal notice on the use of Copernicus Sentinel Data and Service Information",
    target="https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice",
    media_type="application/pdf",
)

LICENSE_PROVIDER: Final[pystac.Provider] = pystac.Provider(
    name="European Commission",
    roles=[ProviderRole.LICENSOR],
    url="https://commission.europa.eu/",
)

SENTINEL_PROVIDER: Final[pystac.Provider] = pystac.Provider(
    name="ESA",
    roles=[ProviderRole.PRODUCER, ProviderRole.PROCESSOR],
    url="https://sentinel.esa.int/web/sentinel/missions",
)

EOPF_PROVIDER: Final[pystac.Provider] = pystac.Provider(
    name="EOPF Sentinel Zarr Samples Service",
    url="https://zarr.eopf.copernicus.eu/",
    roles=[ProviderRole.HOST, ProviderRole.PROCESSOR],
)

THUMBNAIL_ASSET: pystac.Asset = pystac.Asset(
    href="",
    title="",
    media_type="image/png",
    roles=["thumbnail"],
)

PRODUCT_METADATA_PATH: Final[str] = ".zmetadata"
PRODUCT_METADATA_ASSET_KEY: Final[str] = "product_metadata"

PRODUCT_ASSET_KEY: Final[str] = "product"
PRODUCT_ASSET_EXTRA_FIELDS: Final[dict] = {
    "xarray:open_datatree_kwargs": EopfXarrayBackendConfig(mode=OpMode.NATIVE).to_dict()
}

DATASET_ASSET_EXTRA_FIELDS: Final[dict] = {
    "xarray:open_dataset_kwargs": EopfXarrayBackendConfig(mode=OpMode.NATIVE).to_dict()
}

ZIPPED_PRODUCT_ASSET_KEY: Final[str] = "zipped_product"
ZIPPED_PRODUCT_HREF_BASE = "https://download.user.eopf.eodc.eu/zip"

EODC_HDA_DATA_ENDPOINT = "https://data.eodc.eu"
EODC_S3_DATA_ENDPOINT = "https://objects.eodc.eu"

def get_item_asset_metadata() -> ItemAssetDefinition:
    return ItemAssetDefinition.create(
        title="Consolidated Metadata",
        description="Consolidated metadata of the EOPF product",
        media_type=MEDIA_TYPE_JSON,
        roles=[ROLE_METADATA],
    )


def get_item_asset_product():
    return ItemAssetDefinition.create(
        title="EOPF Product",
        description="The full Zarr store of the EOPF product",
        media_type=MEDIA_TYPE_ZARR,
        roles=[ROLE_DATA, ROLE_METADATA],
        extra_fields=deepcopy(PRODUCT_ASSET_EXTRA_FIELDS),
    )


def get_item_asset_zipped_product() -> ItemAssetDefinition:
    return ItemAssetDefinition.create(
        title="Zipped EOPF Product",
        description="The full EOPF Zarr store as zip archive",
        media_type=MEDIA_TYPE_ZIP,
        roles=[ROLE_DATA, ROLE_METADATA, ROLE_ARCHIVE],
    )


PRODUCT_EXTENSION_SCHEMA_URI = "https://stac-extensions.github.io/product/v0.1.0/schema.json"
PROCESSING_EXTENSION_SCHEMA_URI = "https://stac-extensions.github.io/processing/v1.2.0/schema.json"
EOPF_EXTENSION_SCHEMA_URI = "https://cs-si.github.io/eopf-stac-extension/v1.2.0/schema.json"
VERSION_EXTENSION_SCHEMA_URI = "https://stac-extensions.github.io/version/v1.2.0/schema.json"
RASTER_EXTENSION_SCHEMA_URI = "https://stac-extensions.github.io/raster/v2.0.0/schema.json"
EO_EXTENSION_SCHEMA_URI = "https://stac-extensions.github.io/eo/v2.0.0/schema.json"

S2_MGRS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"_T(\d{1,2})([CDEFGHJKLMNPQRSTUVWX])([ABCDEFGHJKLMNPQRSTUVWXYZ][ABCDEFGHJKLMNPQRSTUV])"
)
