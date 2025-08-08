"""
This module provides a dedicated class for downloading media items from URLs.
"""

import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from requests.exceptions import RequestException

_LOGGER = logging.getLogger(__name__)


class MediaDownloader:
    """
    A class to handle the downloading of media files from a given URL.

    This class provides methods to download individual files and
    to process all media items associated with a story.
    """

    def __init__(self, session: requests.Session):
        """
        Initializes the MediaDownloader with an authenticated session.

        Args:
            session: An authenticated requests.Session object.
        """
        self._session = session

    def _sanitize_story_title(self, story_title: str) -> str:
        """Sanitizes story title by removing invalid characters."""
        sanitized = re.sub(r'[^a-zA-Z0-9_-]+', '_', story_title).strip('_')
        return sanitized if sanitized else "untitled"
    
    def _sanitize_story_datetime(self, story_datetime: str) -> str:
        """Sanitizes file name by removing invalid characters."""
        sanitized = re.sub(r'\D', '', story_datetime).strip()
        return sanitized if sanitized else "nodate"

    def _download_file(self, url: str, folder_path: Path, file_name: str) -> bool:
        """
        Downloads a single file from a given URL.

        Args:
            url: The URL of the file to download.
            folder_path: The local folder path as a Path object.
            file_name: The desired file name.

        Returns:
            True on successful download, False otherwise.
        """
        file_path = folder_path / file_name
        folder_path.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            _LOGGER.info("File '%s' already exists. Skipping download.", file_name)
            return True

        try:
            _LOGGER.info("Downloading file from %s to %s...", url, file_path)
            with self._session.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                with file_path.open('wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            _LOGGER.info("Successfully downloaded '%s'.", file_name)
            return True
        except RequestException as e:
            _LOGGER.error("Failed to download file from %s: %s", url, e)
            return False
        except IOError as e:
            _LOGGER.error("Failed to write media to file %s: %s", file_path, e)
            return False

    def download_media_for_story(self, story: Dict[str, Any], download_base_path: str) -> bool:
        """
        Downloads all media for a single story, creating a new subfolder for it.

        Args:
            story: A dictionary representing a single story from the API.
            download_base_path: The base directory to save all downloads.

        Returns:
            True if all media for the story were downloaded, False otherwise.
        """
        story_id = story.get('id')
        story_title = self._sanitize_story_title(story.get('title', f"story_{story_id}"))
        media_items = story.get('media', [])
        
        # Use updated_at or created_at for the date part of the folder name
        story_date_sanitized = self._sanitize_story_datetime(story.get('updated_at', story.get('created_at', '')))

        if not media_items:
            _LOGGER.info("Story '%s' (ID: %s) has no media to download.", story_title, story_id)
            return True

        _LOGGER.info("Processing media for story '%s' (ID: %s)...", story_title, story_id)
        
        # Create a subfolder for the story
        story_folder_name = f"{story_date_sanitized}_{story_id}_{story_title}"
        story_folder_path = Path(download_base_path) / story_folder_name
        story_folder_path.mkdir(parents=True, exist_ok=True)

        all_downloads_successful = True
        for item in media_items:
            file_url = item.get('resized_url') or item.get('cloudfront_feature_url')
            if not file_url:
                _LOGGER.warning("Media item in story %s has no valid URL. Skipping.", story_id)
                continue

            # Determine file extension based on media type
            file_extension = '.mp4' if item.get('type') == 'video' else '.jpg'
            file_name = f"{item.get('id', 'media_item')}{file_extension}"
            _LOGGER.info('-' * 80) # line divider
            # Add a delay to avoid rate-limiting issues
            time.sleep(1)
            
            if not self._download_file(file_url, story_folder_path, file_name):
                all_downloads_successful = False

        return all_downloads_successful
