from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.exceptions import TransportQueryError
import requests
import logging
from .ImageFetchType import ImageFetchType
from typing import Optional
from utils import str_list_to_str, int_list_to_str
import backoff
from gql.dsl import DSLQuery, DSLSchema, dsl_gql, DSLMutation, DSLInlineFragment

class StashAPI:
    """
    API wrapper for Stash.
    """
    
    def __init__(self, url, api_key, username, password):
        """
        Construct a new StashAPI object.

        :param url: URL of the Stash instance.
        :param api_key: API key for the Stash instance.
        :param username: Username for the Stash instance.
        :param password: Password for the Stash instance.
        """
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

        with self.client as session:
            assert self.client.schema is not None
            self.ds = DSLSchema(self.client.schema)

    @backoff.on_exception(backoff.expo, TransportQueryError, max_tries=3)
    def add_performer(self, name:str, disambiguation: Optional[str] = None, tag_ids: Optional[list[int]] = None, alias_list: Optional[list[str]] = None):
        """
        Add a performer to stash.

        :param name: Name of the performer.
        :param disambiguation: Disambiguation of the performer. (optional)
        :param tag_ids: Tag ids of the performer. (optional)
        :param alias_list: List of aliases for the performer. (optional)

        """
        input = {
            "name": name,
        }
        
        if disambiguation is not None:
            input["disambiguation"] = disambiguation

        input['tag_ids'] = [self.default_tag_id]
        if tag_ids is not None:
            input['tag_ids'].extend(tag_ids)

        if alias_list is not None:
            input["alias_list"] = alias_list

        query = dsl_gql(
            DSLMutation(
                self.ds.Mutation.performerCreate.args(
                    input=input
                ).select(
                    self.ds.Performer.id,
                    self.ds.Performer.name
                )
            )
        )

        return self.client.execute(query)
    
    @backoff.on_exception(backoff.expo, TransportQueryError, max_tries=3)
    def get_performer_by_name(self, name: str):
        """
        Get a performer by name.
        
        :param name: Name of the performer.
        """

        query = dsl_gql(
            DSLQuery(
                self.ds.Query.findPerformers.args(
                    performer_filter={
                        "name": {
                            "value": name,
                            "modifier": "EQUALS"
                        }
                    }
                ).select(
                    self.ds.FindPerformersResultType.count,
                    self.ds.FindPerformersResultType.performers.select(
                        self.ds.Performer.id,
                        self.ds.Performer.name
                    )
                )
            )
        )

        return self.client.execute(query)

    @backoff.on_exception(backoff.expo, TransportQueryError, max_tries=3)
    def add_studio(self, studio_name: str):
        """
        Add a studio to stash.
        
        :param studio_name: Name of the studio.
        """

        query = dsl_gql(
            DSLMutation(
                self.ds.Mutation.studioCreate.args(
                    input={
                        "name": studio_name,
                        "details": "stash-booru-tagger"
                    }
                ).select(
                    self.ds.Studio.id,
                    self.ds.Studio.name
                )
            )
        )
        
        return self.client.execute(query)
    
    @backoff.on_exception(backoff.expo, TransportQueryError, max_tries=3)
    def get_studio_by_name(self, studio_name: str):
        """
        Get a studio by name.

        :param studio_name: Name of the studio.
        """

        query = dsl_gql(
            DSLQuery(
                self.ds.Query.findStudios.args(
                    studio_filter={
                        "name": {
                            "value": studio_name,
                            "modifier": "EQUALS"
                        }
                    }
                ).select(
                    self.ds.FindStudiosResultType.count,
                    self.ds.FindStudiosResultType.studios.select(
                        self.ds.Studio.id,
                        self.ds.Studio.name
                    )
                )
            )
        )

        return self.client.execute(query)

    @backoff.on_exception(backoff.expo, TransportQueryError, max_tries=3)
    def add_tag(self, tag_name: str, aliases: Optional[list[str]] = None, parent_ids: Optional[list[int]] = None):
        """
        Add a tag to stash.
        
        :param tag_name: Name of the tag.
        :param aliases: List of aliases for the tag. (optional)
        :param parent_ids: List of parent tag ids for the tag. (optional)
        """
        
        input = {
            "name": tag_name,
        }

        if aliases is not None:
            input["aliases"] = aliases

        if parent_ids is not None:
            input["parent_ids"] = parent_ids

        query = dsl_gql(
            DSLMutation(
                self.ds.Mutation.tagCreate.args(
                    input=input
                ).select(
                    self.ds.Tag.id,
                    self.ds.Tag.name
                )
            )
        )

        return self.client.execute(query)

    @backoff.on_exception(backoff.expo, TransportQueryError, max_tries=3)
    def get_tag_by_name(self, tag_name: str):
        """
        Get a tag by name.

        :param tag_name: Name of the tag.
        """

        query = dsl_gql(
            DSLQuery(
                self.ds.Query.findTags.args(
                    tag_filter={
                        "name": {
                            "value": tag_name,
                            "modifier": "EQUALS"
                        }
                    }
                ).select(
                    self.ds.FindTagsResultType.count,
                    self.ds.FindTagsResultType.tags.select(
                        self.ds.Tag.id,
                        self.ds.Tag.name
                    )
                )
            )
        )

        return self.client.execute(query)

    @backoff.on_exception(backoff.expo, TransportQueryError, max_tries=3)
    def update_image(self, image_id: int, tag_ids: Optional[list[int]] = None, performer_ids: Optional[list[int]] = None, studio_id: Optional[int] = None, urls: Optional[list[str]] = None):
        """
        Update an image in stash.

        :param image_id: Id of the image.
        :param tag_ids: List of tag ids for the image. (optional)
        :param performer_ids: List of performer ids for the image. (optional)
        :param studio_id: Studio id for the image. (optional)
        :param urls: List of urls for the image. (optional)
        """

        input = {
            "id": image_id
        }

        if tag_ids is not None:
            input["tag_ids"] = tag_ids

        if performer_ids is not None:
            input["performer_ids"] = performer_ids

        if studio_id is not None:
            input["studio_id"] = studio_id

        if urls is not None:
            input["urls"] = urls

        query = dsl_gql(
            DSLMutation(
                self.ds.Mutation.imageUpdate.args(
                    input=input
                ).select(
                    self.ds.Image.id
                )
            )
        )

        return self.client.execute(query)

    def load_image(self, image_url: str):
        """
        Downloads an image from stash.

        :param image_url: URL of the image.
        """
        self.logger.info(f"Loading image from {image_url}...")

        image_dl_response = self.request_session.get(image_url)

        if image_dl_response.status_code != 200:
            raise Exception(f"Failed to download image. Status code: {image_dl_response.status_code}")
        
        return image_dl_response.content

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_images(self, type: ImageFetchType, id: Optional[int] = None):
        """
        Fetch images from stash.
        
        :param type: Type of image fetch.
        :param id: Id of the image gallery or single image. (optional)
        """
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

        query = dsl_gql(
            DSLQuery(
                self.ds.Query.findImages.args(
                    filter={
                        "per_page": -1
                    }
                ).select(
                    self.ds.FindImagesResultType.count,
                    self.ds.FindImagesResultType.images.select(
                        self.ds.Image.id,
                        self.ds.Image.paths.select(
                            self.ds.ImagePathsType.image
                        )
                    )
                )
            )
        )

        result = self.client.execute(query)
        return result['findImages']['images']
    
    def _get_image_gallery(self, gallery_id: int):

        query = dsl_gql(
            DSLQuery(
                self.ds.Query.findImages.args(
                    image_filter={
                        "galleries": {
                            "value": gallery_id,
                            "modifier": "INCLUDES"
                        }
                    },
                    filter={
                        "per_page": -1
                    }
                ).select(
                    self.ds.FindImagesResultType.count,
                    self.ds.FindImagesResultType.images.select(
                        self.ds.Image.id,
                        self.ds.Image.paths.select(
                            self.ds.ImagePathsType.image
                        )
                    )
                )
            )
        )

        result = self.client.execute(query)
        return result['findImages']['images']
    
    def _get_single_image(self, image_id: int):

        query = dsl_gql(
            DSLQuery(
                self.ds.Query.findImages.args(
                    image_filter={
                        "id": {
                            "value": image_id,
                            "modifier": "EQUALS"
                        }
                    },
                    filter={
                        "per_page": -1
                    }
                ).select(
                    self.ds.FindImagesResultType.count,
                    self.ds.FindImagesResultType.images.select(
                        self.ds.Image.id,
                        self.ds.Image.paths.select(
                            self.ds.ImagePathsType.image
                        )
                    )
                )
            )
        )

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

        query = dsl_gql(
            DSLQuery(
                self.ds.Query.version.select(
                    self.ds.Version.version
                )
            )
        )

        result = self.client.execute(query)
        self.logger.debug(f"API version: {result['version']['version']}")

        self.default_tag_id = self.create_default_tag()

        self.request_session = requests.Session()
        stash_login_response = self.request_session.post(self.login_url, data=self.login_data)
        if stash_login_response.status_code != 200:
            raise Exception(f"Failed to login to stash. Status code: {stash_login_response.status_code}")
        

        

