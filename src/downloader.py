import os
import logging
import time
import random
import re
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

STORY_ITEM_MEDIA_VIDEO_TYPE = 'video'
STORY_ITEM_MEDIA_IMAGE_TYPE = 'image'
STORY_ITEM_MEDIA_PDF_TYPE = 'image'

def download_file(session: requests.Session, url: str, folder_path: str, file_name: str) -> bool:
    """
    Downloads a single file from a given URL using an authenticated session.

    Args:
        session (requests.Session): The authenticated session object.
        url (str): The URL of the file to download.
        folder_path (str): The local folder path to save the file.
        file_name (str): The desired file name.

    Returns:
        bool: True on successful download, False otherwise.
    """
    file_path = os.path.join(folder_path, file_name)
    os.makedirs(folder_path, exist_ok=True)

    if os.path.exists(file_path):
        logger.info(f"File '{file_name}' already exists. Skipping download.")
        return True

    try:
        logger.info(f"Downloading file from {url} to {file_path}...")
        with session.get(url, stream=True, timeout=30) as response:
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info(f"Successfully downloaded '{file_name}'.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download file from {url}: {e}")
        return False

def download_media_for_story(session: requests.Session, story: Dict[str, Any], download_base_path: str) -> bool:
    """
    Downloads all media (images and videos) for a single story.

    Args:
        session (requests.Session): The authenticated session object.
        story (Dict[str, Any]): The story dictionary from the API response.
        download_base_path (str): The base directory to save all downloads.

    Returns:
        bool: True if all media for the story were downloaded, False otherwise.
    """
    story_id = story.get('id')
    story_title = story.get('title', f"story_{story_id}").strip()
    story_title = re.sub(r'[^a-zA-Z0-9_-]+', '_', story_title).strip('_')
    media_items = story.get('media', [])
    story_date = story.get('updated_at', 'created_at').replace("-", "").replace("T", "").replace(":", "").replace(".", "").replace("Z", "")
    all_downloads_successful = True

    if not media_items:
        logger.info(f"Story '{story_title}' (ID: {story_id}) has no media to download.")
        return True

    logger.info(f"Processing media for story '{story_title}' (ID: {story_id})...")
    
    # Create a subfolder for the story
    story_folder_name = f"{story_date}_{story_id}_{story_title.replace(' ', '_').replace('/', '_')}"
    story_folder_path = os.path.join(download_base_path, story_folder_name)
    os.makedirs(story_folder_path, exist_ok=True)

    for item in media_items:

        file_url = item.get('resized_url') or item.get('cloudfront_feature_url')
        if not file_url:
            logger.warning(f"Media item in story {story_id} has no valid URL. Skipping.")
            continue

        file_extension = ".mp4" if item.get('type') == 'video' else ".jpg"
        file_name = f"{item.get('id', 'media_item')}{file_extension}"
        
        # slepp_time = random.randint(1, 5)
        # logger.info(f"sleeping {slepp_time} seconds for next download")
        logger.info('-' * 80)
        time.sleep(1)

        if not download_file(session, file_url, story_folder_path, file_name):
            all_downloads_successful = False

    return all_downloads_successful