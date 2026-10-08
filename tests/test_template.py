import json
import os
from pathlib import Path

import pytest
import yaml

from eopf_stac.common.constants import (
    PRODUCT_TYPE_TO_COLLECTION,
)
from eopf_stac.io import get_cdse_stac_item_url, register_item
from eopf_stac.stac.factory import StacItemBuilderFactory
from eopf_stac.zarr.reader import ZarrMetadataReaderV3


def test_renders_valid_stac_item():
    try:
        test_config = None
        with Path("test-config.yaml").open("r", encoding="utf-8") as f:
            test_config = yaml.safe_load(f)

        for test in test_config.get("tests_enabled"):
            test_spec = test_config.get("tests").get(test)
            zarr_base_url = test_config.get("zarr_base_url")
            stac_api_url = test_config.get("stac_api_url")
            render_stac_item(test_spec, zarr_base_url, stac_api_url, test_config.get("debug", False))

        pytest.fail(reason="Fail manually to see the logs")

    except Exception as e:
        pytest.fail(reason=(str(e)))


def render_stac_item(test_spec, zarr_base_url, stac_api_url, debug: bool):
    zarr_store_name = test_spec.get("zarr_store_name")
    zarr_store_url = os.path.join(zarr_base_url, zarr_store_name)

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
    if debug:
        print(json.dumps(item.to_dict(), indent=2))

    # Set collection
    item.collection_id = collection

    # Publish to STAC API
    register_item(item, stac_api_url)
