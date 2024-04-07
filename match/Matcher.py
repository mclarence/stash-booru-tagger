from abc import ABC, abstractmethod
from typing import List
from .MatchResults import MatchResult

class Matcher(ABC):
    @abstractmethod
    def match_image(self, image_bytes, image_similarity: float) -> List[MatchResult]:
        pass