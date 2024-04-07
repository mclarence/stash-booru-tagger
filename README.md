# Stash Booru Tagger
Python script to automatically tag your "*anime*" images stored in [Stash](https://github.com/stashapp/stash) based on tag data from booru sites. 

The script will map the following booru tags to stash

| Booru Tag Type   |   | Stash | Notes |
|----------|---|-------|---|
| Character |➡️|Performer| Performer alias will be set to the original tag. The disambiguation will be set to the corresponding copyright tag if it exists
| Copyright |➡️|Tag| Copyright/Series tags will be created as normal tags
| Artist |➡️|Studio| Artist tags will be created as studios
| General |❌|Tag| General tags are currently not transferred over as at the time of writing this script, I did not need the general tags.

## Supported Booru Sites
* Danbooru
* Gelbooru
* Konachan
* Sankaku Complex
* Yandere

## Supported Reverse Image Sites
* IQDB

## Requirements
* Stash instance
    * API Key
    * Stash username and pssword
* Python 3.10+

## Usage
1. Clone repository.
2. Install dependencies.
```
pip install -r requirements.txt
```
3. View help information.
```
usage: main.py [-h] -s STASH_URL -k API_KEY -u STASH_USERNAME -p STASH_PASSWORD [-sm IMAGE_SIMILARITY] [-b {danbooru.donmai.us,gelbooru.com,konachan.com,yande.re,chan.sankakucomplex.com}] [-f] [-sf] [-t MAX_THREADS] (-a | -i STASH_IMAGE_ID | -g STASH_IMAGE_GALLERY_ID)

Tags images in stash from booru site tags.

options:
  -h, --help            show this help message and exit
  -s STASH_URL, --stash-url STASH_URL
                        URL of the stash server.
  -k API_KEY, --api-key API_KEY
                        API key for the stash server.
  -u STASH_USERNAME, --stash-username STASH_USERNAME
                        Username for the stash server. (required for downloading images from stash.)
  -p STASH_PASSWORD, --stash-password STASH_PASSWORD
                        Password for the stash server. (required for downloading images from stash.)
  -sm IMAGE_SIMILARITY, --image-similarity IMAGE_SIMILARITY
                        Minimum similarity for image comparison. (Default 0.9 (90%))
  -b {danbooru.donmai.us,gelbooru.com,konachan.com,yande.re,chan.sankakucomplex.com}, --preferred-booru {danbooru.donmai.us,gelbooru.com,konachan.com,yande.re,chan.sankakucomplex.com}
                        Preferred booru site to source tags from. (Default danbooru)
  -f, --force-tag-all   Force re-tagging of all images.
  -sf, --skip-failed-images
                        Skip images that have failed to process.
  -t MAX_THREADS, --max-threads MAX_THREADS
                        Maximum number of threads to use. (Default 4)
  -a, --stash-all-images
                        Tag all images in stash.
  -i STASH_IMAGE_ID, --stash-image-id STASH_IMAGE_ID
                        Tag a specific image in stash by id.
  -g STASH_IMAGE_GALLERY_ID, --stash-image-gallery-id STASH_IMAGE_GALLERY_ID
                        Tag all images in a specific gallery in stash by id.
```

Please be advised that tagging does take a extremely long time so it is best to leave it overnight if you have a lot of images. Also do not set --max-threads to greater than 4 to avoid being rate limited by boorus and IQDB.

## Example
Tag images using the mystashinstance.com instance using the stash_api_key api key with username stash and password 123456 using gallery id 126 as the source of the image with at max 7 threads.
```
python main.py' -s 'https://mystashinstance.com' '-k' 'stash_api_key' '-u' 'stash' '-p' '123456' '-g' '126' '-t' '7'
```