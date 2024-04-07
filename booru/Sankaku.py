from .Booru import Booru
from .Tags import Tags
import requests
from bs4 import BeautifulSoup
import urllib.parse

class Sankaku(Booru):
    HOST = "chan.sankakucomplex.com"
    API_HOST = "https://capi-v2.sankakucomplex.com"

    def get_tags(self, url: str) -> Tags:
        resp = requests.get(self._parse_url(url))

        if resp.status_code != 200:
            raise Exception("Failed to get tags")
        
        resp_json = resp.json()

        copyright_tags = []
        artist_tags = []
        character_tags = []

        for tag in resp_json['tags']:
            if tag['name_en'] == "///":
                continue

            match tag['type']:
                case 3: #copyright tag
                    copyright_tags.append(tag['name_en'])
                case 4: # character tag
                    character_tags.append(tag['name_en'])
                case 1: # artist tag
                    artist_tags.append(tag['name_en'])

        return Tags(
            artist=artist_tags,
            character=character_tags,
            copyright=copyright_tags,
        )
        
    
    def _parse_url(self, url: str) -> str:
        parse = urllib.parse.urlparse(url)
        path = parse.path.split("/")
        post_id = path[-1]

        return f"{Sankaku.API_HOST}/posts/{post_id}"
