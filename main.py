import argparse
import logging
from gql.transport.requests import log as requests_logger
from stash import StashAPI
from stash import ImageFetchType
from gql.transport.exceptions import TransportQueryError
from match import IqdbMatcher
from booru import BooruEnum, Danbooru, Gelbooru, Konachan, Sankaku, Yandere
from urllib.parse import urlparse
from utils import format_tag, ProgressCounter
import sqlite3
from sqlite3 import IntegrityError
import asyncio
import coloredlogs

async def main(stash_api: StashAPI, args):
    try:
        images = get_images_from_stash(stash_api, args)
        total_images = len(images)
        logger.info(f"Will now process {total_images} images.")
    except TransportQueryError as e:
        logger.error(f"Failed to query stash: {str(e)}")
        return

    logger.info(f"Queuing {total_images} images for processing...")

    task_queue = []
    semaphore = asyncio.Semaphore(args.max_threads)
    counter = ProgressCounter(0)

    for image in images:

        # If the image has been processed and we're not forcing re-tagging, skip it.
        if image_is_processed(image['id']) and not args.force_tag_all:
            logger.info(f"Image {image['id']} has already been processed.")
            # delete from failed images if it exists
            if image_is_failed(image['id']):
                delete_failed_image(image['id'])
            continue

        # If the image has previously failed to process and we're skipping failed images, skip it unless we're forcing re-tagging.
        if (image_is_failed(image['id']) and args.skip_failed_images) or not args.force_tag_all:
            logger.info(f"Image {image['id']} has previously failed to process.")
            continue

        # Queue the image for processing
        task_queue.append(process_image_wrapper(
            semaphore=semaphore,
            image=image,
            counter=counter,
            stash_api=stash_api,
            image_similarity=args.image_similarity,
            preferred_booru=args.preferred_booru
        ))

    total_queue_count = len(task_queue)
    counter.set_total(total_queue_count)

    logger.info(f"Queued {total_queue_count} images for processing.")

    try:
        await asyncio.gather(*task_queue)
    except Exception as e:
        logger.error(f"Failed to process images: {str(e)}")

    logger.info(f"Finished processing images.")

def get_images_from_stash(stash_api: StashAPI, args):
    if args.stash_all_images:
        images = stash_api.get_images(ImageFetchType.ALL_IMAGES)
    elif args.stash_image_id:
        images = stash_api.get_images(ImageFetchType.SINGLE_IMAGE,args.stash_image_id)
    elif args.stash_image_gallery_id:
        images = stash_api.get_images(ImageFetchType.IMAGE_GALLERY,args.stash_image_gallery_id)

    return images

async def process_image_wrapper(semaphore, image, counter, stash_api: StashAPI, image_similarity: float, preferred_booru: BooruEnum):
    async with semaphore:
        logger.info(f"Processing image {image['id']}... [{counter}]")
        try:
            await process_image(stash_api, image, image_similarity, preferred_booru)
            add_processed_image(image['id'])

            # delete from failed images if it exists
            if image_is_failed(image['id']):
                delete_failed_image(image['id'])
        except IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Image {image['id']} has already been processed previously.")
            else:
                logger.warning(f"Unable to keep track of processed image: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to process image: {str(e)}")
            try:
                add_processed_image(image['id'], failed=True, reason=str(e))
            except Exception as e:
                logger.warn(f"Unable to keep track of failed image: {str(e)}")
        finally:
            await counter.increment()


async def process_image(stash_api: StashAPI, image, image_similarity: float, preferred_booru: BooruEnum):
    logger.debug(f"Downloading image {image['paths']['image']}...")
    image_bytes = stash_api.load_image(image['paths']['image'])

    logger.info(f"Matching image {image['id']}...")
    matched_image = await match_image(image_bytes, image_similarity, preferred_booru)
    if matched_image is None:
        raise Exception(f"No matches found for image {image.id}.")
    logger.info(f"Matched image {image['id']} with {matched_image.source_url}.")
    
    logger.info(f"Fetching tags for image {image['id']}...")
    tags = get_matched_image_tags(matched_image.source_url)
        
    copyright_tags_to_assign = []
    character_tags_to_assign = []
    artist_tags_to_assign = []
    
    logger.info(f"Tags found: {tags}")
    logger.info(f"Creating tags on stash...")
    # create the copyright tags as normal tags

    logger.info("Creating copyright/series tags on stash...")
    for copyright_tag in tags.copyright:
        if not copyright_tag:
            continue
        
        logger.debug(f"Creating tag for {copyright_tag}...")

        formatted_tag = format_tag(copyright_tag)
        existing_tag = stash_api.get_tag_by_name(formatted_tag)

        if existing_tag['findTags']['count'] == 0:
            logger.debug(f"Tag {formatted_tag} not found, creating...")
            add_tag = stash_api.add_tag(formatted_tag, [copyright_tag])
            copyright_tags_to_assign.append((add_tag['tagCreate']['id'], add_tag['tagCreate']['name']))
        elif existing_tag['findTags']['count'] > 1:
            raise Exception(f"Multiple tags found for {formatted_tag}.")
        else:
            logger.debug(f"Tag {formatted_tag} exists already. Using existing tag.")
            copyright_tags_to_assign.append((existing_tag['findTags']['tags'][0]['id'], existing_tag['findTags']['tags'][0]['name']))

    # create the character tags as performers
    logger.info("Creating character tags on stash...")
    for character_tag in tags.character:
        if not character_tag:
            continue
        logger.debug(f"Creating performer for {character_tag}...")

        formatted_tag = format_tag(character_tag)
        existing_performer = stash_api.get_performer_by_name(formatted_tag)

        if existing_performer['findPerformers']['count'] == 0:
            logger.debug(f"Performer {formatted_tag} not found, creating...")
            character_tags_to_assign.append(stash_api.add_performer(
                name=formatted_tag,
                disambiguation=copyright_tags_to_assign[0][1] if len(copyright_tags_to_assign) > 0 else "",
                tag_ids=[ids[0] for ids in copyright_tags_to_assign],
                alias_list=[character_tag] if character_tag.lower() != formatted_tag.lower() else []
            )['performerCreate']['id'])
        elif existing_performer['findPerformers']['count'] > 1:
            raise Exception(f"Multiple performers found for {formatted_tag}.")
        else:
            logger.debug(f"Performer {formatted_tag} exists already. Using existing performer.")
            character_tags_to_assign.append(existing_performer['findPerformers']['performers'][0]['id'])

    # create artist tags as studios
    logger.info("Creating artist tags on stash...")
    for artist_tag in tags.artist:
        if artist_tag in ['banned_artist']:
            continue

        logger.debug(f"Creating studio for {artist_tag}...")
        formatted_tag = format_tag(artist_tag)
        existing_studio = stash_api.get_studio_by_name(formatted_tag)

        if existing_studio['findStudios']['count'] == 0:
            logger.debug(f"Studio {formatted_tag} not found, creating...")
            artist_tags_to_assign.append(stash_api.add_studio(formatted_tag)['studioCreate']['id'])
        elif existing_studio['findStudios']['count'] > 1:
            raise Exception(f"Multiple studios found for {formatted_tag}.")
        else:
            logger.debug(f"Studio {formatted_tag} exists already. Using existing studio.")
            artist_tags_to_assign.append(existing_studio['findStudios']['studios'][0]['id'])

    logger.info(f"Assigning tags to image...")
    # now we can assign the tags to the image
    stash_api.update_image(image['id'], [ids[0] for ids in copyright_tags_to_assign], character_tags_to_assign, artist_tags_to_assign[0] if len(artist_tags_to_assign) > 0 else None, [matched_image.source_url])

    logger.info(f"Image {image['id']} processed successfully.")
        
async def match_image(image_bytes, image_similarity: float, preferred_booru: BooruEnum):
    matches = await IqdbMatcher().match_image(image_bytes, image_similarity)

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

def get_matched_image_tags(url):
    matched_image_host = urlparse(url).netloc
    booru_classes = {
        BooruEnum.DANBOORU.value: Danbooru,
        BooruEnum.GELBOORU.value: Gelbooru,
        BooruEnum.KONACHAN.value: Konachan,
        BooruEnum.YANDERE.value: Yandere,
        BooruEnum.SANKAKU.value: Sankaku
    }

    if matched_image_host not in booru_classes:
        raise Exception(f"Unsupported booru site: {matched_image_host}")
    
    booru = booru_classes[matched_image_host]()
    return booru.get_tags(url)

def parse_args():
    parser = argparse.ArgumentParser(description='Tags images in stash from booru site tags.')
    parser.add_argument('-s', '--stash-url', type=str, help='URL of the stash server.', required=True)
    parser.add_argument('-k', '--api-key', type=str, help='API key for the stash server.', required=True)
    parser.add_argument('-u', '--stash-username', type=str, help='Username for the stash server. (required for downloading images from stash.)', required=True)
    parser.add_argument('-p', '--stash-password', type=str, help='Password for the stash server. (required for downloading images from stash.)', required=True)
    parser.add_argument('-sm', '--image-similarity', type=float, help='Minimum similarity for image comparison.', default=0.9)
    parser.add_argument('-b', '--preferred-booru', type=BooruEnum, help='Preferred booru site to source tags from.', choices=list(BooruEnum), default=BooruEnum.DANBOORU)
    parser.add_argument('-f', '--force-tag-all', action='store_true', help='Force re-tagging of all images.', default=False)
    parser.add_argument('-sf', '--skip-failed-images', action='store_true', help='Skip images that have failed to process.')
    parser.add_argument('-t', '--max-threads', type=int, help='Maximum number of threads to use.', default=4)
    stash_image_group = parser.add_mutually_exclusive_group(required=True)

    stash_image_group.add_argument('-a', '--stash-all-images', action='store_true', help='Tag all images in stash.')
    stash_image_group.add_argument('-i', '--stash-image-id', type=int, help='Tag a specific image in stash by id.')
    stash_image_group.add_argument('-g', '--stash-image-gallery-id', type=int, help='Tag all images in a specific gallery in stash by id.')

    return parser.parse_args()

def setup_logging():
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] %(message)s')
    logger = logging.getLogger(__name__)
    coloredlogs.install(level='DEBUG', logger=logger)
    requests_logger.setLevel(logging.WARNING)
    return logger

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

def delete_processed_image(image_id):
    cursor = tagger_db.cursor()
    cursor.execute('DELETE FROM processed_images WHERE id = ?', (image_id,))
    tagger_db.commit()

def delete_failed_image(image_id):
    cursor = tagger_db.cursor()
    cursor.execute('DELETE FROM failed_images WHERE id = ?', (image_id,))
    tagger_db.commit()

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
        exit(1)

    asyncio.run(main(stash_api, args))