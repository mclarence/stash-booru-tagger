from .Booru import Booru
from .Tags import Tags
import requests
from bs4 import BeautifulSoup
class Yandere(Booru):
    HOST = "yande.re"

    def get_tags(self, url: str) -> Tags:
        resp = requests.get(url)

        if resp.status_code != 200:
            raise Exception("Failed to get tags")
        
        soup = BeautifulSoup(resp.content, 'html.parser')

        # API not used as tags are not separated by type in the API response.
        html_artist_tags = soup.find_all('li', class_=lambda x: x and 'tag-type-artist' in x)
        html_copyright_tags = soup.find_all('li', class_=lambda x: x and 'tag-type-copyright' in x)
        html_character_tags = soup.find_all('li', class_=lambda x: x and 'tag-type-character' in x)

        return Tags(
            artist=self._parse_li(html_artist_tags),
            character=self._parse_li(html_character_tags),
            copyright=self._parse_li(html_copyright_tags),
        )

    def _parse_li(self, li_tag):
        tags = []
        for el in li_tag:
            a_tags = el.find_all('a')

            if len(a_tags) >= 2:
                tags.append(a_tags[1].text)
        return tags