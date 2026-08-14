from typing import Protocol, runtime_checkable

import pystac


@runtime_checkable
class StacItemBuilder(Protocol):
    def build(self, metadata: dict, url: str, collection: str) -> pystac.Item: ...
