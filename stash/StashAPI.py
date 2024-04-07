from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import requests
import logging
from .ImageFetchType import ImageFetchType
from typing import Optional
from utils import format_tag, str_list_to_str, int_list_to_str
import backoff

class StashAPI:
    def __init__(self, url, api_key, username, password):
        self.logger = logging.getLogger(__name__)
        self.url = url
        self.graphql_url = f"{self.url}/graphql"
        self.api_key = api_key
        self.login_url = f"{self.url}/login"
        self.username = username
        self.password = password
        self.headers = {
            "ApiKey": self.api_key,
        }
        self.login_data = {
            "username": self.username,
            "password": self.password,
        }
        self.request_session = requests.Session()
        self.transport = RequestsHTTPTransport(url=self.graphql_url, headers=self.headers)
        self.client = Client(transport=self.transport, fetch_schema_from_transport=True)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def add_performer(self, name:str, disambiguation:str, tag_ids: list[int], alias_list: list[str]):
        tag_ids.append(self.default_tag_id)

        query = """
            mutation {{
                performerCreate(input:{{
                    name: "{}"
                    disambiguation: "{}"
                    tag_ids: [{}]
                    alias_list: [{}]
                }}) {{
                    id
                    name
                }}
            }}
            """.format(name, disambiguation, int_list_to_str(tag_ids) , str_list_to_str(alias_list))
        
        return self.client.execute(gql(query))
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_performer_by_name(self, name: str):
        query = """
            query {{
                findPerformers(performer_filter: {{name: {{value: "{}", modifier: EQUALS}}}}) {{
                    count
                    performers {{
                        id
                        name
                    }}
                }}
            }}

        """.format(name)
        performer_query = gql(query)

        return self.client.execute(performer_query)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def add_studio(self, studio_name: str):
        query = """
            mutation {{
                studioCreate(input:{{
                    name: "{}"
                    details: "stash-booru-tagger"
                }}) {{
                    id
                    name
                }}
            }}
            """.format(studio_name)
        
        return self.client.execute(gql(query))
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_studio_by_name(self, studio_name: str):
        query = """
            query {{
                findStudios(studio_filter: {{name: {{value: "{}", modifier: EQUALS}}}}) {{
                    count
                    studios {{
                        id
                        name
                    }}
                }}
            }}

        """.format(studio_name)
        studio_query = gql(query)

        return self.client.execute(studio_query)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def add_tag(self, tag_name: str, aliases: list[str]):
        query = """
        mutation {{
            tagCreate(input: {{
                name: "{}"
                aliases: [{}]
                parent_ids: [{}]
            }}) {{
                id
                name
            }}
            }}
        """.format(tag_name, str_list_to_str(aliases), self.default_tag_id)

        return self.client.execute(gql(query))
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def add_default_tag(self, tag_name: str, aliases: list[str]):
        query = """
        mutation {{
            tagCreate(input: {{
                name: "{}"
                aliases: [{}]
            }}) {{
                id
                name
            }}
            }}
        """.format(tag_name, str_list_to_str(aliases))

        return self.client.execute(gql(query))

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_tag_by_name(self, tag_name: str):
        query = """
            query {{
                findTags(tag_filter: {{name: {{value: "{}", modifier: EQUALS}}}}) {{
                    count
                    tags {{
                        id
                        name
                    }}
                }}
            }}

        """.format(tag_name)
        tag_query = gql(query)

        return self.client.execute(tag_query)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def update_image(self, image_id: int, tag_ids: list[int], performer_ids: list[int], studio_id: int, urls: list[str]):

        if studio_id is None:
            query =  """
            mutation {{
                imageUpdate(input: {{
                    id: {}
                    tag_ids: [{}]
                    performer_ids: [{}]
                    urls: [{}]
                }}) {{
                    id
                }}
            }}
            """.format(image_id, int_list_to_str(tag_ids), int_list_to_str(performer_ids), str_list_to_str(urls))
        else:
            query =  """
            mutation {{
                imageUpdate(input: {{
                    id: {}
                    tag_ids: [{}]
                    performer_ids: [{}]
                    studio_id: {}
                    urls: [{}]
                }}) {{
                    id
                }}
            }}
            """.format(image_id, int_list_to_str(tag_ids), int_list_to_str(performer_ids), studio_id, str_list_to_str(urls))

        return self.client.execute(gql(query))

    def load_image(self, image_url: str):
        self.logger.info(f"Loading image from {image_url}...")

        image_dl_response = self.request_session.get(image_url)

        if image_dl_response.status_code != 200:
            raise Exception(f"Failed to download image. Status code: {image_dl_response.status_code}")
        
        return image_dl_response.content

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_images(self, type: ImageFetchType, id: Optional[int] = None):
        match type:
            case ImageFetchType.ALL_IMAGES:
                return self._get_all_images()
            case ImageFetchType.IMAGE_GALLERY:
                if id is None:
                    raise Exception("Image gallery id required for fetching image gallery.")
                return self._get_image_gallery(id)
            case ImageFetchType.SINGLE_IMAGE:
                if id is None:
                    raise Exception("Image id required for fetching single image.")
                return self._get_single_image(id)
            case other:
                raise Exception(f"Invalid image fetch type: {type}")
            
    def _get_all_images(self):
        self.logger.info("Fetching all images...")
        query = gql("""
            query {
                findImages(
                    filter: {
                        per_page: -1
                    }
                ) {
                    count
                    images {
                        id
                        paths {
                            image
                        }
                    }
                }
            }
        """)

        result = self.client.execute(query)
        return result['findImages']['images']
    
    def _get_image_gallery(self, gallery_id: int):
        query = gql("""
            query {{
                findImages(
                    image_filter: {{
                        galleries: {{
                            value: {}
                            modifier: INCLUDES
                        }}
                    }},
                    filter: {{
                        per_page: -1
                    }}
                ) {{
                    count
                    images {{
                        id
                        paths {{
                            image
                        }}
                    }}
                }}
            }}
        """.format(gallery_id))

        result = self.client.execute(query)
        return result['findImages']['images']
    
    def _get_single_image(self, image_id: int):
        query = gql("""
            query {{
                findImages(
                    image_filter: {{
                        id: {{
                            value: {}
                            modifier: EQUALS
                        }}
                    }},
                    filter: {{
                        per_page: -1
                    }}
                ) {{
                    count
                    images {{
                        id
                        paths {{
                            image
                        }}
                    }}
                }}
            }}
        """.format(image_id))

        result = self.client.execute(query)
        return result['findImages']['images']
    
    def create_default_tag(self):
        tag = self.get_tag_by_name("stash-booru-tagger")

        if tag['findTags']['count'] == 0:
            tag = self.add_default_tag("stash-booru-tagger", [])
            return tag['id']
        else:
            return tag['findTags']['tags'][0]['id']
    
    def check_api(self):
        self.logger.info("Checking API...")

        query = gql("""
            query {
                version {
                    version
                }
            }
        """)

        result = self.client.execute(query)
        self.logger.debug(f"API version: {result['version']['version']}")

        self.default_tag_id = self.create_default_tag()

        self.request_session = requests.Session()
        stash_login_response = self.request_session.post(self.login_url, data=self.login_data)
        if stash_login_response.status_code != 200:
            raise Exception(f"Failed to login to stash. Status code: {stash_login_response.status_code}")
        

        

