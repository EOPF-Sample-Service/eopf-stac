from typing import List, Protocol, runtime_checkable

import pystac


@runtime_checkable
class StacItemBuilder(Protocol):
    def build(self, metadata: dict, url: str, collection: str) -> List[pystac.Item]: ...
