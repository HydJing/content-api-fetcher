"""Provides a class for scraping stories from an API with pagination and checkpoints."""

import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from requests.exceptions import RequestException

# Import the new MediaDownloader class
from .downloader import MediaDownloader

# Use a consistent logger for the module
_LOGGER = logging.getLogger(__name__)


class StoryScraper:
    """A class to fetch stories from an API with pagination and checkpoint support.

    This class manages the API interaction, including handling pagination tokens,
    retrying failed requests, and saving progress.
    """

    # Class-level constant for the checkpoint file path
    CHECKPOINT_PATH = Path("last_processed_page_token.json")

    def __init__(self, session: requests.Session, base_api_url: str, child_id: str):
        """Initialize the StoryScraper with the necessary dependencies.

        Args:
        ----
            session: An authenticated requests.Session object.
            base_api_url: The base URL for the API endpoints.
            child_id: The ID of the child to fetch stories for.

        """
        self._session = session
        self._base_api_url = base_api_url
        self._child_id = child_id
        self._media_downloader = MediaDownloader(session=session)

    def _load_checkpoint(self) -> str | None:
        """Load the last processed page token from the checkpoint file.

        Returns:
        -------
            The page token as a string, or None if the file is not found or invalid.

        """
        if not self.CHECKPOINT_PATH.exists():
            _LOGGER.info("Checkpoint file not found. Starting from the beginning.")
            return None

        try:
            with open(self.CHECKPOINT_PATH, encoding="utf-8") as f:
                checkpoint_data = json.load(f)
            page_token = checkpoint_data.get("page_token")
            if page_token:
                _LOGGER.info(f"Resuming from page token: {page_token}")
                return page_token
            _LOGGER.warning(
                "Checkpoint file is malformed. Starting from the beginning."
            )
            return None
        except (OSError, json.JSONDecodeError, KeyError) as e:
            _LOGGER.error(
                f"Error loading checkpoint file: {e}. Starting from the beginning."
            )
            return None

    def _save_checkpoint(self, page_token: str):
        """Save the last processed page token to a checkpoint file.

        Args:
        ----
            page_token: The page token to save.

        """
        checkpoint_data = {"page_token": page_token, "timestamp": time.time()}
        try:
            with open(self.CHECKPOINT_PATH, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f)
            _LOGGER.info(f"Pagination checkpoint saved. Next page token: {page_token}")
        except (OSError, TypeError) as e:
            _LOGGER.error(f"Failed to save pagination checkpoint: {e}")

    def _fetch_api_page(self, page_token: str | None) -> dict[str, Any] | None:
        """Fetch a single page of story data from the API.

        Args:
        ----
            page_token: The token for the next page, or None for the first page.

        Returns:
        -------
            The JSON response as a dictionary, or None on failure.

        """
        stories_endpoint = f"children/{self._child_id}/stories"
        full_api_url = urljoin(self._base_api_url, stories_endpoint)
        params = {"sort_by": "updated_at", "story_type": "all"}
        if page_token:
            params["page_token"] = page_token

        try:
            _LOGGER.info(
                f"Fetching API data from: {full_api_url} with token: {page_token}"
            )
            response = self._session.get(full_api_url, params=params, timeout=20)
            response.raise_for_status()

            return response.json()
        except RequestException as e:
            _LOGGER.error(f"Failed to fetch API data from {full_api_url}: {e}")
            return None
        except json.JSONDecodeError:
            _LOGGER.error(
                "Failed to decode JSON from API response. Response text: %s...",
                response.text[:200],
            )
            return None

    def download_all_stories(self, download_base_path: str):
        """Fetch all stories with associated media.

        Args:
        ----
            download_base_path: The local path to save downloaded files.

        """
        page_token = self._load_checkpoint()

        while True:
            api_response = self._fetch_api_page(page_token)

            if not api_response or not api_response.get("stories"):
                _LOGGER.info(
                    "No more pages or stories to fetch. Pagination is complete."
                )
                break

            stories_on_page = api_response.get("stories", [])
            _LOGGER.info(
                f"Processing {len(stories_on_page)} stories from the current page."
            )

            for story in stories_on_page:
                download_successful = self._media_downloader.download_media_for_story(
                    story, download_base_path
                )
                if not download_successful:
                    # Stop the process to retry this page later If a download fails.
                    _LOGGER.error(
                        "A download failed. "
                        "Stopping the scraping process to resume later."
                    )
                    self._save_checkpoint(
                        page_token
                    )  # Save the current page token before exiting
                    return

            page_token = api_response.get("next_page_token")

            if not page_token:
                _LOGGER.info("Reached the end of all pages.")
                break

            self._save_checkpoint(page_token)
            _LOGGER.info(
                f"Next page token: {page_token}. Pausing before next request..."
            )
            _LOGGER.info("=" * 80)  # line divider
            time.sleep(1)  # Consider using an exponential backoff or jitter here
