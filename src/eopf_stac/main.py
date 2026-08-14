import argparse
import json
import logging
import os
from sys import exit
from typing import Optional

from eopf_stac.common.constants import PRODUCT_TYPE_TO_COLLECTION
from eopf_stac.io import get_cdse_stac_item_url, register_item
from eopf_stac.stac.factory import StacItemBuilderFactory
from eopf_stac.zarr.reader import ZarrMetadataReaderV3

logger = logging.getLogger(__name__)

ENV_STAC_API_URL: str = "STAC_API_URL"
ENV_STAC_INGEST_USER: str = "STAC_INGEST_USER"
ENV_STAC_INGEST_PASS: str = "STAC_INGEST_PASS"
ENV_S3_ENDPOINT_URL: str = "S3_ENDPOINT_URL"
ENV_AWS_ACCESS_KEY_ID: str = "AWS_ACCESS_KEY_ID"
ENV_AWS_SECRET_ACCESS_KEY: str = "AWS_SECRET_ACCESS_KEY"


def configure_logging(level: int):
    logging.basicConfig(
        level=level,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def validate_env(url: str, dry_run: bool, output_file: Optional[str], source_uri: str, env):
    if url.startswith("s3://"):
        # if s3 url is provided, the credentials are required?
        missing_vars = []
        if ENV_S3_ENDPOINT_URL not in env:
            missing_vars.append(ENV_S3_ENDPOINT_URL)

        if ENV_AWS_ACCESS_KEY_ID not in env:
            missing_vars.append(ENV_AWS_ACCESS_KEY_ID)

        if ENV_AWS_SECRET_ACCESS_KEY not in env:
            missing_vars.append(ENV_AWS_SECRET_ACCESS_KEY)

        if len(missing_vars) > 0:
            raise ValueError(f"The following enviroment variables are missing: {missing_vars}")

    if not dry_run and not output_file:
        if ENV_STAC_API_URL not in env:
            raise ValueError(f"The enviroment variable {ENV_STAC_API_URL} is missing")

    if source_uri is None or len(source_uri) == 0:
        logger.warning("No value for --source-uri provided. Some STAC properties might not be available!")


def exit_on_error(exit_code: int = 1):
    logger.error("Exit on error")
    exit(exit_code)


def main():
    parser = argparse.ArgumentParser("eopf-stac.py")
    parser.add_argument("URL", help="Local file path or URL to the EOPF product", type=str)
    parser.add_argument(
        "--source-uri",
        help="Reference to the original product which was input for the EOPF conversion",
        action="store",
    )
    parser.add_argument(
        "--dry-run", help="Create STAC item without trying to insert it into the catalog", action="store_true"
    )
    parser.add_argument("--output-file", help="Save the STAC item as JSON to the specified file path", type=str)
    parser.add_argument("--debug", help="Enable verbose output", action="store_true")
    args = parser.parse_args()

    if args.debug:
        configure_logging(logging.DEBUG)
    else:
        configure_logging(logging.INFO)

    try:
        validate_env(args.URL, args.dry_run, args.output_file, args.source_uri, os.environ)

        # Read metadata
        reader = ZarrMetadataReaderV3()
        zarr_json, product_type = reader.read(args.URL)

        # Check if collection for product type is defined
        try:
            collection = PRODUCT_TYPE_TO_COLLECTION[product_type]
        except KeyError:
            raise ValueError(f"No Zarr v3 collection defined for product type {product_type}")

        # Determine CDSE STAC item url
        if args.source_uri is not None and len(args.source_uri) > 0:
            logger.info(f"Retrieving STAC item url from CDSE for {args.source_uri}")
            cdse_stac_item_url = get_cdse_stac_item_url(args.source_uri, product_type)
        else:
            cdse_stac_item_url = None

        # Create STAC item
        logger.info(f"Creating STAC item for product_type {product_type} and url {args.URL} ...")
        item = StacItemBuilderFactory().create(product_type).build(zarr_json, args.URL, cdse_stac_item_url)
        logger.debug(json.dumps(item.to_dict(), indent=2))

        # Set collection
        item.collection_id = collection

        if not args.dry_run:
            if args.output_file:
                logger.info(f"Writing STAC item to {args.output_file}")
                with open(args.output_file, "w") as f:
                    json.dump(item.to_dict(), f, indent=4)
            else:
                logger.info(f"Registering STAC item to {os.environ[ENV_STAC_API_URL]}")
                item = register_item(item=item, stac_api_url=os.environ[ENV_STAC_API_URL])

    except Exception as e:
        logger.error(str(e))
        exit_on_error()


if __name__ == "__main__":
    main()
