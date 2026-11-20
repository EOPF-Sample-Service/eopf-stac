from eopf_stac.stac.builder import StacItemBuilder
from eopf_stac.stac.sentinel1 import StacItemBuilderS1GRD, StacItemBuilderS1SLC
from eopf_stac.stac.sentinel2 import StacItemBuilderS2

STAC_ITEM_BUILDERS = {
    "S02MSIL2A": StacItemBuilderS2,
    "S02MSIL1C": StacItemBuilderS2,
    "S01SIWGRD": StacItemBuilderS1GRD,
    "S01SEWGRD": StacItemBuilderS1GRD,
    "S01SIWSLC": StacItemBuilderS1SLC,
}


class StacItemBuilderFactory:
    def create(self, product_type: str) -> StacItemBuilder:
        try:
            return STAC_ITEM_BUILDERS[product_type](product_type)
        except KeyError:
            raise ValueError(f"Unsupported product type {product_type}")
