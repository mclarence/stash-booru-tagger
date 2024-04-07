import argparse
import logging
from gql.transport.requests import log as requests_logger
from stash import StashAPI
from stash import ImageFetchType
from gql.transport.exceptions import TransportQueryError
from match import IqdbMatcher
from booru import BooruEnum, Danbooru, Gelbooru, Konachan, Sankaku, Yandere
from urllib.parse import urlparse
from utils import format_tag
import sqlite3

def main(stash_api: StashAPI, args):
    try:
        if args.stash_all_images:
            images = stash_api.get_images(ImageFetchType.ALL_IMAGES)
            total_images = len(images)
            logger.info(f"Tagging {total_images} images...")
        elif args.stash_image_id:
            images = stash_api.get_images(ImageFetchType.SINGLE_IMAGE,args.stash_image_id)
            total_images = len(images)
            logger.info(f"Tagging image {args.stash_image_id}...")
        elif args.stash_image_gallery_id:
            images = stash_api.get_images(ImageFetchType.IMAGE_GALLERY,args.stash_image_gallery_id)
            total_images = len(images)
            logger.info(f"Tagging {total_images} images in gallery {args.stash_image_gallery_id}...")
    except TransportQueryError as e:
        logger.error(f"Failed to query stash: {str(e)}")

    processed_count = 0
    for image in images:
        logger.info(f"Processing image {image['id']}... [{processed_count}/{total_images}]")

        if image_is_processed(image['id']) and not args.force_tag_all:
            logger.info(f"Image {image['id']} has already been processed.")
            processed_count += 1
            continue

        if image_is_failed(image['id']) and not args.skip_failed_images:
            logger.info(f"Image {image['id']} has previously failed to process.")
            processed_count += 1
            continue

        try:
            process_image(stash_api, image, args.image_similarity, args.preferred_booru)
            add_processed_image(image['id'])
        except Exception as e:
            logger.error(f"Failed to process image: {str(e)}")
            add_processed_image(image['id'], failed=True, reason=str(e))
        
        processed_count += 1

def process_image(stash_api: StashAPI, image, image_similarity: float, preferred_booru: BooruEnum):
    image_bytes = stash_api.load_image(image['paths']['image'])
    matched_image = match_image(image_bytes, image_similarity, preferred_booru)
    if matched_image is None:
        raise Exception(f"No matches found for image {image.id}.")
    
    matched_image_host = urlparse(matched_image.source_url).netloc

    match matched_image_host:
        case BooruEnum.DANBOORU.value:
            danbooru = Danbooru()
            tags = danbooru.get_tags(matched_image.source_url)
        case BooruEnum.GELBOORU.value:
            gelbooru = Gelbooru()
            tags = gelbooru.get_tags(matched_image.source_url)
        case BooruEnum.KONACHAN.value:
            konachan = Konachan()
            tags = konachan.get_tags(matched_image.source_url)
        case BooruEnum.YANDERE.value:
            yandere = Yandere()
            tags = yandere.get_tags(matched_image.source_url)
        case BooruEnum.SANKAKU.value:
            sankaku = Sankaku()
            tags = sankaku.get_tags(matched_image.source_url)
        case _:
            raise Exception(f"Unsupported booru site: {matched_image_host}")
        
    copyright_tags_to_assign = []
    character_tags_to_assign = []
    artist_tags_to_assign = []
    
    logger.info(f"Tags found: {tags}")
    logger.info(f"Creating tags on stash...")
    # create the copyright tags as normal tags
    for copyright_tag in tags.copyright:
        formatted_tag = format_tag(copyright_tag)
        existing_tag = stash_api.get_tag_by_name(formatted_tag)

        if existing_tag['findTags']['count'] == 0:
            add_tag = stash_api.add_tag(formatted_tag, [copyright_tag])
            copyright_tags_to_assign.append((add_tag['tagCreate']['id'], add_tag['tagCreate']['name']))
        elif existing_tag['findTags']['count'] > 1:
            raise Exception(f"Multiple tags found for {formatted_tag}.")
        else:
            copyright_tags_to_assign.append((existing_tag['findTags']['tags'][0]['id'], existing_tag['findTags']['tags'][0]['name']))

    # create the character tags as performers
    for character_tag in tags.character:
        formatted_tag = format_tag(character_tag)
        existing_performer = stash_api.get_performer_by_name(formatted_tag)

        if existing_performer['findPerformers']['count'] == 0:
            character_tags_to_assign.append(stash_api.add_performer(
                name=formatted_tag,
                disambiguation=copyright_tags_to_assign[0][1] if len(copyright_tags_to_assign) > 0 else "",
                tag_ids=[ids[0] for ids in copyright_tags_to_assign],
                alias_list=[character_tag]
            )['performerCreate']['id'])
        elif existing_performer['findPerformers']['count'] > 1:
            raise Exception(f"Multiple performers found for {formatted_tag}.")
        else:
            character_tags_to_assign.append(existing_performer['findPerformers']['performers'][0]['id'])

    # create artist tags as studios
    for artist_tag in tags.artist:
        formatted_tag = format_tag(artist_tag)
        existing_studio = stash_api.get_studio_by_name(formatted_tag)

        if existing_studio['findStudios']['count'] == 0:
            artist_tags_to_assign.append(stash_api.add_studio(formatted_tag)['studioCreate']['id'])
        elif existing_studio['findStudios']['count'] > 1:
            raise Exception(f"Multiple studios found for {formatted_tag}.")
        else:
            artist_tags_to_assign.append(existing_studio['findStudios']['studios'][0]['id'])

    logger.info(f"Assigning tags to image...")
    # now we can assign the tags to the image
    stash_api.update_image(image['id'], [ids[0] for ids in copyright_tags_to_assign], character_tags_to_assign, artist_tags_to_assign[0] if len(artist_tags_to_assign) > 0 else None, [matched_image.source_url])

    logger.info(f"Image {image['id']} processed successfully.")
        
def match_image(image_bytes, image_similarity: float, preferred_booru: BooruEnum):
    matches = IqdbMatcher().match_image(image_bytes, image_similarity)

    if len(matches) == 0:
        return matches
    
    best_match = None

    for match in matches:
        # Check if the match has similarity >= image_similarity
        if match.image_similarity >= image_similarity:
            # If preferred booru match found, return immediately
            if preferred_booru.value in match.source_url:
                return match
            # Update the best match if it's None or if the current match has higher similarity
            if best_match is None or match.image_similarity > best_match.image_similarity:
                best_match = match

    # Return the best match found (which may be None if no matches found)

    return best_match

def parse_args():
    parser = argparse.ArgumentParser(description='Tags images in stash from booru site tags.')
    parser.add_argument('-s', '--stash-url', type=str, help='URL of the stash server.', required=True)
    parser.add_argument('-k', '--api-key', type=str, help='API key for the stash server.', required=True)
    parser.add_argument('-u', '--stash-username', type=str, help='Username for the stash server. (required for downloading images from stash.)', required=True)
    parser.add_argument('-p', '--stash-password', type=str, help='Password for the stash server. (required for downloading images from stash.)', required=True)
    parser.add_argument('-sm', '--image-similarity', type=float, help='Minimum similarity for image comparison.', default=0.9)
    parser.add_argument('-b', '--preferred-booru', type=BooruEnum, help='Preferred booru site to source tags from.', choices=list(BooruEnum), default=BooruEnum.DANBOORU)
    parser.add_argument('-f', '--force-tag-all', action='store_true', help='Force re-tagging of all images.', default=False)
    parser.add_argument('-sf', '--skip-failed-images', action='store_true', help='Skip images that have failed to process.', default=False)
    stash_image_group = parser.add_mutually_exclusive_group(required=True)

    stash_image_group.add_argument('-a', '--stash-all-images', action='store_true', help='Tag all images in stash.')
    stash_image_group.add_argument('-i', '--stash-image-id', type=int, help='Tag a specific image in stash by id.')
    stash_image_group.add_argument('-g', '--stash-image-gallery-id', type=int, help='Tag all images in a specific gallery in stash by id.')

    return parser.parse_args()

def setup_logging():
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] %(message)s')
    requests_logger.setLevel(logging.WARNING)
    return logging.getLogger(__name__)

def add_processed_image(image_id, failed=False, reason=None):
    cursor = tagger_db.cursor()
    if failed:
        cursor.execute('INSERT INTO failed_images (id, reason) VALUES (?, ?)', (image_id, reason))
    else:
        cursor.execute('INSERT INTO processed_images (id) VALUES (?)', (image_id,))
    tagger_db.commit()

def image_is_processed(image_id) -> bool:
    cursor = tagger_db.cursor()
    cursor.execute('SELECT * FROM processed_images WHERE id = ?', (image_id,))
    return cursor.fetchone() is not None

def image_is_failed(image_id) -> bool:
    cursor = tagger_db.cursor()
    cursor.execute('SELECT * FROM failed_images WHERE id = ?', (image_id,))
    return cursor.fetchone() is not None

def setup_sqlite():
    con = sqlite3.connect('tagger.db')

    # create the tables if they don't exist
    con.execute('''
        CREATE TABLE IF NOT EXISTS processed_images (
            id INTEGER PRIMARY KEY
        );
    ''')

    con.execute('''
        CREATE TABLE IF NOT EXISTS failed_images (
            id INTEGER PRIMARY KEY,
            reason TEXT
        );
    ''')

    con.commit()

    return con

if __name__ == '__main__':
    args = parse_args()
    global logger
    logger = setup_logging()
    global tagger_db
    tagger_db = setup_sqlite()
    
    stash_api = StashAPI(args.stash_url, args.api_key, args.stash_username, args.stash_password)
    try:
        stash_api.check_api()
    except Exception as e:
        logging.critical(f"Failed to check API: {str(e)}")
    pass

    main(stash_api, args)