from abc import ABC, abstractmethod
from .Tags import Tags

class Booru(ABC):
    @abstractmethod
    def get_tags(self, url: str) -> Tags:
        pass