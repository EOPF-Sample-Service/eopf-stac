import json
import logging
import os
from urllib.parse import urlparse

import fsspec
import pystac
import requests
import s3fs
from pystac.utils import datetime_to_str, now_in_utc

from eopf_stac.common.constants import (
    CDSE_STAC_API_URL,
    PRODUCT_METADATA_PATH,
    PRODUCT_TYPE_TO_CDSE_COLLECTION,
    PRODUCT_TYPE_TO_COLLECTION,
    SUPPORTED_PRODUCT_TYPES_S1,
    SUPPORTED_PRODUCT_TYPES_S2,
    SUPPORTED_PRODUCT_TYPES_S3,
)
from eopf_stac.common.stac import get_cpm_version, validate_metadata
from eopf_stac.sentinel1.stac import create_item as create_item_s1
from eopf_stac.sentinel2.stac import create_item as create_item_s2
from eopf_stac.sentinel3.stac import create_item as create_item_s3

logger = logging.getLogger(__name__)


def read_metadata(eopf_href: str) -> dict:
    path = os.path.join(eopf_href, PRODUCT_METADATA_PATH)
    fs = fsspec.filesystem("file")

    if eopf_href.startswith("s3://"):
        fs = s3fs.S3FileSystem(anon=False, endpoint_url=os.environ["S3_ENDPOINT_URL"])
    elif eopf_href.startswith("http"):
        o = urlparse(eopf_href)
        endpoint_url = f"{o.scheme}://{o.netloc}"
        path = os.path.join(o.path, PRODUCT_METADATA_PATH)
        fs = s3fs.S3FileSystem(anon=True, client_kwargs={"endpoint_url": endpoint_url})

        # unregister handler to make boto3 work with CEPH
        handlers = fs.s3.meta.events._emitter._handlers
        handlers_to_unregister = handlers.prefix_search("before-parameter-build.s3")
        handler_to_unregister = handlers_to_unregister[0]
        fs.s3.meta.events._emitter.unregister("before-parameter-build.s3", handler_to_unregister)

    # -- open product metadata
    f = fs.open(path, "rb")
    zmetadata = json.load(f)

    return validate_metadata(zmetadata)


def create_item(metadata: dict, eopf_href: str, source_uri: str | None) -> pystac.Item:
    # Determine product type
    product_type = metadata[".zattrs"]["stac_discovery"].get("properties", {}).get("product:type")
    # workaround eopf-cpm 2.4.x
    if product_type is None:
        product_type = metadata[".zattrs"]["stac_discovery"].get("properties", {}).get("eopf:type")
    if product_type is None:
        raise ValueError("No product type in stac_discovery metadata")
    logger.info(f"Product type is {product_type}")

    collection = PRODUCT_TYPE_TO_COLLECTION.get(product_type)
    if collection is None:
        raise ValueError(f"No collection defined for product type '{product_type}'")

    # Extract CPM version from eopf_href
    cpm_version = get_cpm_version(eopf_href)
    logger.info(f"CPM version is {cpm_version}")

    # CDSE scene id and href
    cdse_scene_id = None
    if source_uri is not None and len(source_uri) > 0:
        cdse_scene_id = get_cdse_identifier(source_uri)
        logger.info(f"CDSE scene ID is {cdse_scene_id}")
    else:
        logger.warning("No value for --source-uri provided. Some STAC properties might not be available!")

    logger.info(f"Retrieving STAC item url from CDSE for {source_uri}")
    cdse_stac_item_url = get_cdse_stac_item_url(source_uri, product_type)

    item = None
    if product_type in SUPPORTED_PRODUCT_TYPES_S1:
        item = create_item_s1(
            metadata=metadata,
            product_type=product_type,
            asset_href_prefix=eopf_href,
            cpm_version=cpm_version,
            cdse_scene_id=cdse_scene_id,
            cdse_scene_href=cdse_stac_item_url,
            collection_id=collection,
        )
    elif product_type in SUPPORTED_PRODUCT_TYPES_S2:
        item = create_item_s2(
            metadata=metadata,
            product_type=product_type,
            asset_href_prefix=eopf_href,
            cpm_version=cpm_version,
            cdse_scene_id=cdse_scene_id,
            cdse_scene_href=cdse_stac_item_url,
            collection_id=collection,
        )
    elif product_type in SUPPORTED_PRODUCT_TYPES_S3:
        item = create_item_s3(
            metadata=metadata,
            product_type=product_type,
            asset_href_prefix=eopf_href,
            cpm_version=cpm_version,
            cdse_scene_id=cdse_scene_id,
            cdse_scene_href=cdse_stac_item_url,
            collection_id=collection,
        )
    else:
        raise ValueError(f"The product type '{product_type}' is not supported")

    item.collection_id = collection

    logger.info("Sucessfully created STAC item")
    return item


def register_item(item: pystac.Item, stac_api_url: str) -> pystac.Item:
    logger.info(f"Insert/update STAC item {item.id} at catalog {stac_api_url} ...")

    item.remove_links("self")
    session = requests.Session()
    if "STAC_INGEST_USER" in os.environ and "STAC_INGEST_PASS" in os.environ:
        session.auth = (os.environ["STAC_INGEST_USER"], os.environ["STAC_INGEST_PASS"])

    api_action = "inserted"
    item.properties["published"] = datetime_to_str(now_in_utc())
    r = session.post(f"{stac_api_url}/collections/{item.collection_id}/items", json=item.to_dict())
    if r.status_code == 409:
        # STAC item already exists -> update
        item.common_metadata.updated = now_in_utc()

        # try to keep original created and published timestamps
        try:
            existing_item = session.get(f"{stac_api_url}/collections/{item.collection_id}/items/{item.id}").json()
            item.properties["published"] = existing_item["properties"]["published"]
            item.properties["created"] = existing_item["properties"]["created"]
        except Exception as _:
            pass

        api_action = "updated"
        r = session.put(
            f"{stac_api_url}/collections/{item.collection_id}/items/{item.id}",
            json=item.to_dict(),
        )
    r.raise_for_status()
    logger.info(f"Successfully {api_action} STAC item {item.id} in collection {item.collection_id}")

    return item


def get_cdse_identifier(source_uri: str | None) -> str:
    source_identifier = None
    if source_uri is not None and len(source_uri) > 0:
        if source_uri.endswith("/"):
            source_uri = source_uri[:-1]
        source_identifier = source_uri.split("/")[-1]
        if source_identifier.lower().endswith(".safe") or source_identifier.lower().endswith(".sen3"):
            source_identifier = os.path.splitext(source_identifier)[0]
    return source_identifier


def get_cdse_stac_item_url(source_uri: str | None, product_type: str) -> str | None:
    try:
        cdse_stac_item_id = get_cdse_identifier(source_uri)
        if cdse_stac_item_id is not None and len(cdse_stac_item_id) > 0:
            logger.info(f"CDSE STAC item id is {cdse_stac_item_id}")
            collection = PRODUCT_TYPE_TO_CDSE_COLLECTION[product_type]
            cdse_stac_item_url = f"{CDSE_STAC_API_URL}/collections/{collection}/items/{cdse_stac_item_id}"
            # Check if item really exists
            response = requests.get(cdse_stac_item_url)
            response.raise_for_status()
            logger.info(f"CDSE STAC item url is {cdse_stac_item_url}")
            return cdse_stac_item_url
        else:
            raise ValueError("Could not detemine CDSE STAC item id")

    except Exception as e:
        logger.warning(f"Failed to determine STAC item url at CSDE: {str(e)}")
        return None
