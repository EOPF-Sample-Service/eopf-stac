import json
import logging
import os
import re

import geojson
import pystac
import shapely
from footprint_facility import rework_to_polygon_geometry
from pystac import Asset, Link
from pystac.extensions.grid import GridExtension
from pystac.extensions.sat import OrbitState, SatExtension
from pystac.extensions.timestamps import TimestampsExtension
from pystac.utils import now_in_utc, str_to_datetime
from stactools.sentinel2.mgrs import MgrsExtension

from eopf_stac.common.constants import (
    EO_EXTENSION_SCHEMA_URI,
    EOPF_EXTENSION_SCHEMA_URI,
    PROCESSING_EXTENSION_SCHEMA_URI,
    PRODUCT_EXTENSION_SCHEMA_URI,
    S2_MGRS_PATTERN,
    VERSION_EXTENSION_SCHEMA_URI,
    ZIPPED_PRODUCT_HREF_BASE,
    EODC_S3_DATA_ENDPOINT,
    EODC_HDA_DATA_ENDPOINT,
    get_item_asset_zipped_product,
)

logger = logging.getLogger(__name__)


def validate_metadata(metadata: dict) -> dict:
    stac_discovery = metadata.get("metadata", {}).get(".zattrs", {}).get("stac_discovery")
    if stac_discovery is None:
        raise ValueError("JSON object 'stac_discovery' not found in .zmetadata file")

    other_metadata = metadata.get("metadata", {}).get(".zattrs", {}).get("other_metadata")
    if other_metadata is None:
        raise ValueError("JSON object 'other_metadata' not found in .zmetadata file")

    return metadata["metadata"]


def rearrange_bbox(bbox):
    longitudes = [bbox[0], bbox[2]]
    latitudes = [bbox[1], bbox[3]]

    corrected_bbox = [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]
    return corrected_bbox


def get_identifier_from_href(product_href: str):
    if product_href.endswith("/"):
        item_id = os.path.basename(product_href[:-1])
    else:
        item_id = os.path.basename(product_href)

    if item_id.lower().endswith(".safe") or item_id.lower().endswith(".sen3") or item_id.lower().endswith(".zarr"):
        item_id = os.path.splitext(item_id)[0]

    return item_id


def get_identifier(stac_discovery: dict):
    item_id = stac_discovery.get("id")
    # CPM workaround for https://gitlab.eopf.copernicus.eu/cpm/eopf-cpm/-/issues/690
    if item_id.lower().endswith(".safe") or item_id.lower().endswith(".sen3"):
        item_id = os.path.splitext(item_id)[0]
    return item_id


def get_datetimes(properties: dict):
    datetime = None
    start_datetime = None
    end_datetime = None

    start_datetime_str = properties.get("start_datetime")
    if start_datetime_str is not None:
        start_datetime = str_to_datetime(start_datetime_str)

    end_datetime_str = properties.get("end_datetime")
    if end_datetime_str is not None:
        end_datetime = str_to_datetime(end_datetime_str)

    datetime_str = properties.get("datetime")
    if datetime_str is not None:
        # CPM workaround for https://gitlab.eopf.copernicus.eu/cpm/eopf-cpm/-/issues/643
        if datetime_str == "null":
            datetime = start_datetime
        else:
            datetime = str_to_datetime(datetime_str)
    else:
        datetime = start_datetime

    return (datetime, start_datetime, end_datetime)


def get_cpm_version(path: str) -> str | None:
    # matches "cpm_v256"
    p = re.compile("cpm_v[0-9]+")
    m = p.search(path)
    if m is not None:
        g = m.group()
        cpm_version = f"{g[5]}.{g[6]}.{g[7]}"
        return cpm_version

    # matches "cpm-2.5.9"
    p = re.compile("(cpm-([0-9]\.)*[0-9])")
    m = p.search(path)
    if m is not None:
        g = m.group()
        cpm_version = f"{g[4]}.{g[6]}.{g[8]}"
        return cpm_version

    return None


def fix_geometry(item: pystac.Item) -> None:
    coordinates = geojson.Polygon.clean_coordinates(coords=item.geometry["coordinates"], precision=15)
    first_coord = coordinates[0][0]
    last_coord = coordinates[0][-1]
    if first_coord != last_coord:
        # CPM workaround for https://gitlab.eopf.copernicus.eu/cpm/eopf-cpm/-/issues/708
        logger.info("Fixing coordinates to end linear ring where it started")
        coordinates[0].append(first_coord)
        item.geometry["coordinates"] = coordinates

    geometry = shapely.from_geojson(json.dumps(item.geometry))
    reworked = rework_to_polygon_geometry(geometry)
    item.geometry = json.loads(shapely.to_geojson(reworked))


def fill_timestamp_properties(item: pystac.Item, properties: dict) -> None:
    # created_datetime_str = properties.get("created")
    # created_datetime = None
    # if created_datetime_str is None:
    created_datetime = now_in_utc()
    # else:
    #    created_datetime = str_to_datetime(created_datetime_str)
    item.common_metadata.created = created_datetime
    item.common_metadata.updated = created_datetime

    ts_ext = TimestampsExtension.ext(item, add_if_missing=True)
    ts_ext.apply(published=created_datetime)


def fill_sat_properties(item: pystac.Item, properties: dict) -> None:
    orbit_state = properties.get("sat:orbit_state")
    abs_orbit = properties.get("sat:absolute_orbit")
    rel_orbit = properties.get("sat:relative_orbit")
    anx_datetime = properties.get("sat:anx_datetime")
    platform_international_designator = properties.get("sat:platform_international_designator")

    if any_not_none([orbit_state, abs_orbit, rel_orbit, anx_datetime, platform_international_designator]):
        sat_ext = SatExtension.ext(item, add_if_missing=True)
        if orbit_state:
            sat_ext.orbit_state = OrbitState(orbit_state.lower())
        if abs_orbit:
            sat_ext.absolute_orbit = int(abs_orbit)
        if rel_orbit:
            sat_ext.relative_orbit = int(rel_orbit)
        if anx_datetime:
            sat_ext.anx_datetime = str_to_datetime(anx_datetime)
        if platform_international_designator:
            sat_ext.platform_international_designator = platform_international_designator


def fill_eo_properties(item: pystac.Item, properties: dict) -> None:
    cloud_cover = properties.get("eo:cloud_cover")
    snow_cover = properties.get("eo:snow_cover")

    if cloud_cover is not None:
        item.properties["eo:cloud_cover"] = cloud_cover
    if snow_cover is not None:
        item.properties["eo:snow_cover"] = snow_cover

    item.stac_extensions.append(EO_EXTENSION_SCHEMA_URI)


def fill_processing_properties(
    item: pystac.Item, properties: dict, cpm_version: str = None, baseline_processing_version: str = None
) -> None:
    proc_expression = properties.get("processing:expression")
    proc_lineage = properties.get("processing:lineage")
    proc_level = properties.get("processing:level")
    proc_facility = properties.get("processing:facility")
    if type(proc_facility) is list and len(proc_facility) > 0:
        proc_facility = proc_facility[0]
    proc_datetime = properties.get("processing:datetime")
    proc_software = properties.get("processing:software")
    proc_version = properties.get("processing:version")
    if any_not_none([proc_expression, proc_facility, proc_level, proc_lineage, proc_software, proc_datetime]):
        item.stac_extensions.append(PROCESSING_EXTENSION_SCHEMA_URI)
        if proc_expression is not None and proc_expression != "systematic":
            item.properties["processing:expression"] = proc_expression
        if proc_software is not None:
            # CPM workaround
            if proc_software.get("name") is None and proc_software.get("version") is None:
                item.properties["processing:software"] = proc_software
            else:
                item.properties["processing:software"] = {}
        if proc_datetime is not None:
            item.properties["processing:datetime"] = proc_datetime
        if is_valid_string(proc_facility):
            item.properties["processing:facility"] = proc_facility
        if is_valid_string(proc_level):
            item.properties["processing:level"] = proc_level
        if is_valid_string(proc_lineage):
            item.properties["processing:lineage"] = proc_lineage

    # Add CPM to processing:software
    if cpm_version is not None:
        if proc_software is None:
            item.properties["processing:software"] = {}
        item.properties["processing:software"]["EOPF-CPM"] = cpm_version

    if is_valid_string(proc_version) and proc_version != "TODO":
        item.properties["processing:version"] = proc_version
    else:
        # Add baseline version extracted from identifier
        if is_valid_string(baseline_processing_version):
            item.properties["processing:version"] = baseline_processing_version
        else:
            logger.warning("Unable to populate processing:version field")


def fill_product_properties(item: pystac.Item, product_type: str, properties: dict) -> None:
    product_timeliness = properties.get("product:timeliness")
    product_timeliness_category = properties.get("product:timeliness_category")
    product_acquisition_type = properties.get("product:acquisition_type")
    if any_not_none([product_type, product_acquisition_type, all([product_timeliness, product_timeliness_category])]):
        item.stac_extensions.append(PRODUCT_EXTENSION_SCHEMA_URI)
        if is_valid_string(product_type):
            item.properties["product:type"] = product_type
        if is_valid_string(product_acquisition_type):
            item.properties["product:acquisition_type"] = product_acquisition_type
        if all([is_valid_string(product_timeliness), is_valid_string(product_timeliness_category)]):
            # CPM workaround for https://gitlab.eopf.copernicus.eu/cpm/eopf-cpm/-/issues/706
            if product_timeliness != "MISSING":
                item.properties["product:timeliness"] = product_timeliness
                item.properties["product:timeliness_category"] = product_timeliness_category


def fill_eopf_properties(item: pystac.Item, properties: dict) -> None:
    """Fills the item with values of the EOPF STAC extension
    See also: https://github.com/CS-SI/eopf-stac-extension
    """
    datatake_id = properties.get("eopf:datatake_id")
    # CPM workaround for https://gitlab.eopf.copernicus.eu/cpm/eopf-cpm/-/issues/689
    if datatake_id is None:
        datatake_id = properties.get("eopf:data_take_id")
    datastrip_id = properties.get("eopf:datastrip_id")
    instrument_mode = properties.get("eopf:instrument_mode")
    origin_datetime = properties.get("eopf:origin_datetime")
    instrument_configuration_id = properties.get("eopf:instrument_configuration_id")

    if any_not_none(
        [
            datatake_id,
            datastrip_id,
            instrument_mode,
            origin_datetime,
            instrument_configuration_id,
        ]
    ):
        item.stac_extensions.append(EOPF_EXTENSION_SCHEMA_URI)
        if datatake_id is not None:
            item.properties["eopf:datatake_id"] = datatake_id
        if instrument_mode is not None:
            # CPM workaround
            if instrument_mode != "Earth Observation":
                item.properties["eopf:instrument_mode"] = instrument_mode
        if origin_datetime:
            item.properties["eopf:origin_datetime"] = origin_datetime
        if datastrip_id is not None:
            item.properties["eopf:datastrip_id"] = datastrip_id
        if instrument_configuration_id is not None:
            item.properties["eopf:instrument_configuration_id"] = instrument_configuration_id


def fill_mgrs_grid_properties(item: pystac.Item, identifier: str) -> bool:
    success = False
    if identifier is not None:
        mgrs_match = S2_MGRS_PATTERN.search(identifier)
        success = mgrs_match and len(mgrs_groups := mgrs_match.groups())
        if success:
            mgrs = MgrsExtension.ext(item, add_if_missing=True)
            mgrs.utm_zone = int(mgrs_groups[0])
            mgrs.latitude_band = mgrs_groups[1]
            mgrs.grid_square = mgrs_groups[2]
            grid = GridExtension.ext(item, add_if_missing=True)
            grid.code = f"MGRS-{mgrs.utm_zone}{mgrs.latitude_band}{mgrs.grid_square}"
    return success


def fill_version_properties(item: pystac.Item) -> None:
    if item is not None:
        item.properties["deprecated"] = False
        item.stac_extensions.append(VERSION_EXTENSION_SCHEMA_URI)


def is_valid_string(value: str) -> bool:
    return value is not None and len(value) > 0


def any_not_none(values: list) -> bool:
    for v in values:
        if v is not None:
            return True


def create_cdse_link(cdse_scene_href: str) -> Link:
    return Link(
        rel="alternate",
        title="CDSE STAC item",
        target=cdse_scene_href,
        media_type="application/geo+json",
    )


def create_zipped_product_asset(
    eopf_href: str,
    collection_id: str,
    item_id: str
) -> Asset:

    if is_valid_string(collection_id) and is_valid_string(item_id):
        if eopf_href.startswith(EODC_S3_DATA_ENDPOINT):
            href = os.path.join(ZIPPED_PRODUCT_HREF_BASE, "collections", collection_id, "items", item_id + ".zip")
        elif eopf_href.startswith(EODC_HDA_DATA_ENDPOINT):
            href = f"{eopf_href}.zip"
        else:
            raise ValueError(
                f"Unable to create zip product asset: unrecognised endpoint {eopf_href}"
            )
        return get_item_asset_zipped_product().create_asset(href=href)
    else:
        raise ValueError(f"Unable to create zip product asset for collection={collection_id} and item={item_id}")
