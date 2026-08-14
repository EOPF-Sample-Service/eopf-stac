import json
import logging
import os
from urllib.parse import urlparse

import fsspec
import s3fs

logger = logging.getLogger(__name__)


class ZarrMetadataReaderV3:
    ZARR_METADATA_FILE = "zarr.json"

    def read(self, url: str) -> tuple[dict, str]:
        logger.debug(f"Reading Zarr v3 metadata file from {url}")

        try:
            fs = fsspec.filesystem("file")
            if url.startswith("s3://"):
                fs = s3fs.S3FileSystem(anon=False, endpoint_url=os.environ["S3_ENDPOINT_URL"])
            elif url.startswith("http"):
                o = urlparse(url)
                endpoint_url = f"{o.scheme}://{o.netloc}"
                path = os.path.join(o.path, self.ZARR_METADATA_FILE)
                fs = s3fs.S3FileSystem(anon=True, client_kwargs={"endpoint_url": endpoint_url})

                # unregister handler to make boto3 work with CEPH
                handlers = fs.s3.meta.events._emitter._handlers
                handlers_to_unregister = handlers.prefix_search("before-parameter-build.s3")
                handler_to_unregister = handlers_to_unregister[0]
                fs.s3.meta.events._emitter.unregister("before-parameter-build.s3", handler_to_unregister)
            else:
                path = os.path.join(url, self.ZARR_METADATA_FILE)

            f = fs.open(path, "rb")
            zarr_json = json.load(f)

        except Exception as e:
            raise ValueError(f"Unable to open Zarr v3 metadata file: {repr(e)}")

        try:
            product_type = zarr_json["attributes"]["stac_discovery"]["properties"]["product:type"]
            return (zarr_json, product_type)
        except KeyError:
            raise ValueError(f"Unable to determine EOPF product type from Zarr metadata file {self.ZARR_METADATA_FILE}")
