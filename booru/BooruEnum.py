from enum import Enum

class BooruEnum(Enum):
    DANBOORU = 'danbooru.donmai.us'
    GELBOORU = 'gelbooru.com'
    KONACHAN = 'konachan.com'
    YANDERE = 'yande.re'
    SANKAKU = 'chan.sankakucomplex.com'

    def __str__(self) -> str:
        return self.value