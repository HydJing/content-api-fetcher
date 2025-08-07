import requests
import logging
import json
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from requests.exceptions import RequestException
from urllib.parse import urljoin

from .downloader import download_media_for_story

logger = logging.getLogger(__name__)

# Define the path for the checkpoint file
CHECKPOINT_PATH = Path("last_processed_page_token.json")

def _save_pagination_checkpoint(page_token: str):
    """Saves the last processed page token to a checkpoint file."""
    checkpoint_data = {'page_token': page_token, 'timestamp': time.time()}
    try:
        with open(CHECKPOINT_PATH, "w") as f:
            json.dump(checkpoint_data, f)
        logger.info(f"Pagination checkpoint saved. Next page token: {page_token}")
    except (IOError, TypeError) as e:
        logger.error(f"Failed to save pagination checkpoint: {e}")

def _load_pagination_checkpoint() -> Optional[str]:
    """Loads the last processed page token from the checkpoint file."""
    if not CHECKPOINT_PATH.exists():
        logger.error(f"Check point tracking file not found, Create one now.")
        _save_pagination_checkpoint('0')

    try:
        with open(CHECKPOINT_PATH, "r") as f:
            checkpoint_data = json.load(f)
        page_token = checkpoint_data.get('page_token')
        if page_token is not None:
            logger.info(f"Pagination checkpoint found. Resuming from page token: {page_token}")
            return page_token
        else:
            logger.warning("Checkpoint file is empty or malformed. Starting from the beginning.")
            return None
    except (json.JSONDecodeError, KeyError, IOError) as e:
        logger.error(f"Error loading checkpoint file: {e}. Starting from the beginning.")
        return None

def fetch_api_data(session: requests.Session, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Uses an authenticated session to fetch data from an API endpoint.
    """
    try:
        logger.info(f"Fetching API data from: {url} with params: {params}")
        response = session.get(url, params=params, timeout=20)
        response.raise_for_status()
        
        return response.json()
    except RequestException as e:
        logger.error(f"Failed to fetch API data from {url}: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from API response for {url}. Response text: {response.text[:200]}...")
        return None

def get_all_stories(session: requests.Session, base_api_url: str, child_id: str, download_base_path: str) -> None:
    """
    Fetches all stories for a given child ID, handling pagination and downloads the media.
    """
    # Load the page token from the checkpoint, or start from "0"
    page_token = _load_pagination_checkpoint() or "0"
    
    stories_endpoint = f"children/{child_id}/stories"
    full_api_url = urljoin(base_api_url, stories_endpoint)

    while page_token is not None:
        params = {
            "page_token": page_token,
            "sort_by": "updated_at",
            "story_type": "all"
        }
        
        api_response = fetch_api_data(session, full_api_url, params=params)

        if api_response and 'stories' in api_response:
            stories_on_page = api_response.get('stories', [])
            
            for story in stories_on_page:
                story_id = str(story.get('id'))
                # Download media for the story
                if download_media_for_story(session, story, download_base_path):
                    logger.info(f"Successfully processed and downloaded media for story ID: {story_id}")
                else:
                    logger.warning(f"Skipping checkpoint save for story {story_id} due to download failure.")
                    # If a download fails, we stop the process to retry this page later
                    return
            
            logger.info("All stories from the current page have been processed.")
            
            # Get the next page token from the response
            page_token = api_response.get('next_page_token')
            
            if page_token:
                logger.info(f"Next page token: {page_token}. Pausing before next request...")
                _save_pagination_checkpoint(page_token) # Save the checkpoint before the next request
                # slepp_time = random.randint(5, 15)
                # logger.info(f"sleeping {slepp_time} seconds for next call")
                logger.info('=' * 80)
                time.sleep(1)
                
            else:
                logger.info("No more pages to fetch for stories. Pagination is complete.")
        else:
            logger.warning("API response did not contain 'stories' or was empty. Stopping pagination.")
            page_token = None
