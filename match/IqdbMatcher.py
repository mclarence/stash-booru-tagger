from .Matcher import Matcher
from PicImageSearch.model import IqdbResponse
from PicImageSearch.sync import Iqdb as IqdbSync
import backoff
from typing import List
from .MatchResults import MatchResult
import logging
class IqdbMatcher(Matcher):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        super().__init__()

    @backoff.on_exception(backoff.expo, Exception, max_tries=2)
    def match_image(self, image_bytes, image_similarity: float):
        iqdb = IqdbSync(timeout=60.0)
        self.logger.info("Searching for image...")
        resp = iqdb.search(file=image_bytes)
        return self._parse_response(resp)

    def _parse_response(self, resp: IqdbResponse) -> List[MatchResult]:
        return [MatchResult(image_similarity=result.similarity*100, source_url=result.url) for result in resp.raw]