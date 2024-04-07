from dataclasses import dataclass
from typing import List
@dataclass
class Tags:
    character: List[str]
    artist: List[str]
    copyright: List[str]