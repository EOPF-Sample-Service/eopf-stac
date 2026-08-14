import json
import os

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from eopf_stac.common.constants import (
    PRODUCT_TYPE_TO_COLLECTION,
)
from eopf_stac.io import get_cdse_stac_item_url, register_item
from eopf_stac.stac.factory import StacItemBuilderFactory
from eopf_stac.zarr.reader import ZarrMetadataReaderV3


@pytest.fixture
def env():
    return Environment(
        loader=FileSystemLoader("src/eopf_stac/stac/templates/"),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


# BASE_URL = "https://objects.eodc.eu/e05ab01a9d56408d82ac32d69a5aae2a:notebook-data/test_cpm/cpm_v300rc4a"
BASE_URL = "https://objects.eodc.eu/e05ab01a9d56408d82ac32d69a5aae2a:sample-data/eopf-sample-output/geozarr"
STAC_API_URL = "https://stac.core.eopf.eodc.eu"

S02MSIL2A = {
    "template": "S02MSIL2A.json.j2",
    "zarr_store_name": "S2C_MSIL2A_20260716T100601_N0512_R022_T32UQU_20260716T152417.zarr",
    "base_url": BASE_URL,
    "stac_api_url": STAC_API_URL,
    "source_uri": "S2C_MSIL2A_20260716T100601_N0512_R022_T32UQU_20260716T152417.SAFE",
}

S02MSIL1C = {
    "template": "S02MSIL1C.json.j2",
    "zarr_store_name": "S2A_MSIL1C_20260721T102041_N0512_R065_T32UPU_20260721T153621.zarr",
    "base_url": BASE_URL,
    "stac_api_url": STAC_API_URL,
    "source_uri": "S2A_MSIL1C_20260721T102041_N0512_R065_T32UPU_20260721T153621.SAFE",
}


@pytest.fixture(scope="module", params=[S02MSIL1C, S02MSIL2A])
def test_spec(request):
    return request.param


def test_renders_valid_stac_item(env, test_spec):
    base_url = test_spec.get("base_url")
    zarr_store_name = test_spec.get("zarr_store_name")
    zarr_store_url = os.path.join(base_url, zarr_store_name)

    try:
        # Read metadata
        reader = ZarrMetadataReaderV3()
        zarr_json, product_type = reader.read(zarr_store_url)

        # Check if collection for product type is defined
        try:
            collection = PRODUCT_TYPE_TO_COLLECTION[product_type]
        except KeyError:
            raise ValueError(f"No Zarr v3 collection defined for product type {product_type}")

        # CDSE STAC item url
        source_uri = test_spec.get("source_uri")
        print(f"Retrieving STAC item url from CDSE for {source_uri}")
        cdse_stac_item_url = get_cdse_stac_item_url(source_uri, product_type)

        # Create STAC item
        print(f"Creating STAC item for product_type {product_type} and url {zarr_store_url} ...")
        item = StacItemBuilderFactory().create(product_type).build(zarr_json, zarr_store_url, cdse_stac_item_url)
        print(json.dumps(item.to_dict(), indent=2))

        # Set collection
        item.collection_id = collection

        # Publish to STAC API
        stac_api_url = test_spec.get("stac_api_url")
        register_item(item, stac_api_url)

        pytest.fail(reason="Failed manually to see printed output")

    except Exception as e:
        pytest.fail(reason=(str(e)))
