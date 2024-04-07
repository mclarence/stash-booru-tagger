from dataclasses import dataclass

@dataclass
class MatchResult:
    image_similarity: float
    source_url: str