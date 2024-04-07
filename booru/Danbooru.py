from .Booru import Booru
from .Tags import Tags
import requests

class Danbooru(Booru):
    HOST = "danbooru.donmai.us"

    def get_tags(self, url: str) -> Tags:
        resp = requests.get(self._parse_url(url))

        if resp.status_code != 200:
            raise Exception("Failed to get tags")
        
        resp_json = resp.json()

        # check if required tags are present
        if 'tag_string_character' not in resp_json or 'tag_string_artist' not in resp_json or 'tag_string_copyright' not in resp_json:
            raise Exception("Invalid response from Danbooru API. Missing required tags.")
        
        return Tags(
            character=resp_json['tag_string_character'].split(" "),
            artist=resp_json['tag_string_artist'].split(" "),
            copyright=resp_json['tag_string_copyright'].split(" "),
        )
    
    def _parse_url(self, url: str) -> str:
        return url + ".json"