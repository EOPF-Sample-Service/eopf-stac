import json
import os

import pystac
import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pystac.utils import datetime_to_str, now_in_utc

from eopf_stac.common.constants import PRODUCT_TYPE_TO_COLLECTION
from eopf_stac.common.stac import fix_geometry, get_identifier_from_href, get_zipped_zarr_store_url
from eopf_stac.io import register_item
from eopf_stac.zarr.reader import ZarrMetadataReaderV3

BASE_URL = "https://objects.eodc.eu/e05ab01a9d56408d82ac32d69a5aae2a:sample-data/eopf-sample-output/geozarr"
STAC_API_URL = "https://stac.core.eopf.eodc.eu"


S01SIWSLC_1 = {
    "template": "S01SIWSLC.json.j2",
    "zarr_store_name": "S1A_IW_SLC__1SDV_20250819T045501_20250819T045531_060600_0789BF_B9C4.zarr",
    "base_url": BASE_URL,
    "stac_api_url": STAC_API_URL,
    "source_uri": None,
}

S01SIWSLC_2 = {
    "template": "S01SIWSLC.json.j2",
    "zarr_store_name": "S1C_IW_SLC__1SDV_20260731T234807_20260731T234821_008794_0116E8_C079.zarr",
    "base_url": BASE_URL,
    "stac_api_url": STAC_API_URL,
    "source_uri": None,
}


@pytest.fixture
def env():
    return Environment(
        loader=FileSystemLoader("src/eopf_stac/stac/templates/"),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


@pytest.fixture(scope="module", params=[S01SIWSLC_1, S01SIWSLC_2])
def test_spec(request):
    return request.param


def get_eopf_stac_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("eopf-stac")
    except PackageNotFoundError:
        __version__ = "unknown"

    return __version__


def test_renders_valid_stac_item(env, test_spec):
    base_url = test_spec.get("base_url")
    zarr_store_name = test_spec.get("zarr_store_name")
    zarr_store_url = os.path.join(base_url, zarr_store_name)

    # Read metadata
    reader = ZarrMetadataReaderV3()
    zarr_metadata, product_type = reader.read(zarr_store_url)
    collection = PRODUCT_TYPE_TO_COLLECTION[product_type]
    identifier = get_identifier_from_href(zarr_store_url)
    zipped_zarr_store_href = get_zipped_zarr_store_url(zarr_store_url, collection, identifier)

    bursts = {}
    for key in zarr_metadata["consolidated_metadata"]["metadata"].keys():
        k = key.split("/")[0]
        if k not in bursts:
            # S01SIWSLC_20250819T045501_0030_A346_B9C4_0789BF_IW1_327474
            parts = k.split("_")
            swath = parts[6]
            burst_id = int(parts[7])
            burst_zarr_store_url = os.path.join(zarr_store_url, k)
            processing_software = zarr_metadata["attributes"]["stac_discovery"]["properties"]["processing:software"]
            processing_software["eopf-stac"] = get_eopf_stac_version()

            bursts[k] = {
                "id": get_identifier_from_href(burst_zarr_store_url),
                "created": datetime_to_str(now_in_utc()),
                "burst_zarr_group_href": burst_zarr_store_url,
                "zarr_store_href": zarr_store_url,
                "zarr_store_zipped_href": zipped_zarr_store_href,
                "cdse_item_uri": None,
                "processing_software": processing_software,
                "processing:version": zarr_metadata["attributes"]["stac_discovery"]["properties"][
                    "processing:software"
                ]["Sentinel-1 IPF"],
                "swath": [swath],
                "burst_id": burst_id,
            }

    print(f"{len(bursts)} bursts found")

    for name, derived_data in bursts.items():
        burst_zarr_metadata = zarr_metadata["consolidated_metadata"]["metadata"][name]

        template_file_path = f"{product_type}.json.j2"
        template = env.get_template(template_file_path)
        rendered = template.render(zarr=burst_zarr_metadata, extra=derived_data)

        # Fails if JSON syntax is invalid
        data = json.loads(rendered)
        # print(json.dumps(data, indent=2))

        # Fails if JSON does not represent valid STAC item
        item = pystac.Item.from_dict(data)

        # Apply some geometry corrections
        fix_geometry(item)
        # item.bbox = rearrange_bbox(item.bbox)
        from shapely.geometry import shape

        geom = shape(item.geometry)
        item.bbox = geom.bounds

        # Validate item
        print(json.dumps(item.to_dict(), indent=2))
        item.validate()

        # Set collection
        item.collection_id = collection

        # Publish to STAC API
        stac_api_url = STAC_API_URL
        register_item(item, stac_api_url)

    pytest.fail(reason="Failed manually to see the logs")
