"""Manages user authentication with CSRF protection and caches sessions."""

import json
import logging
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

_LOGGER = logging.getLogger(__name__)


class AuthClient:
    """A client to handle user authentication for a website using CSRF protection.

    This client manages the session state, including caching cookies to avoid
    repeated logins.
    """

    # Define class-level constants for cache management
    SESSION_CACHE_PATH = Path("login_session_cache.json")
    SESSION_EXPIRATION_SECONDS = 86400  # 24 hours

    def __init__(self, login_url: str, username: str, password: str):
        """Initialize the AuthClient with login credentials.

        Args:
        ----
            login_url: The API endpoint for authentication.
            username: The user's username (e.g., email).
            password: The user's password.

        """
        self._login_url = login_url
        self._username = username
        self._password = password
        self.session = requests.Session()

    def _load_session_cookies(self) -> bool:
        """Load cookies from a cache file if they are not expired.

        Returns:
        -------
            True if a valid session was loaded, False otherwise.

        """
        if not self.SESSION_CACHE_PATH.exists():
            return False

        try:
            with open(self.SESSION_CACHE_PATH, encoding="utf-8") as f:
                cookies_data = json.load(f)

            created_at = cookies_data.get("created_at")
            if (
                not created_at
                or (time.time() - created_at) > self.SESSION_EXPIRATION_SECONDS
            ):
                _LOGGER.info("Cached session has expired. Deleting cache file.")
                self.SESSION_CACHE_PATH.unlink(missing_ok=True)
                return False

            self.session.cookies.update(cookies_data["cookies"])
            _LOGGER.info("Authenticated session loaded from cache.")
            return True
        except (OSError, json.JSONDecodeError, KeyError) as e:
            _LOGGER.error(f"Error loading session cache: {e}. Deleting corrupted file.")
            self.SESSION_CACHE_PATH.unlink(missing_ok=True)
            return False

    def _save_session_cookies(self):
        """Save the current session's cookies to a cache file."""
        cookies = {
            "cookies": self.session.cookies.get_dict(),
            "created_at": time.time(),
        }
        try:
            with open(self.SESSION_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cookies, f)
            _LOGGER.info("Session cookies saved to cache.")
        except (OSError, TypeError) as e:
            _LOGGER.error(f"Failed to save session cache: {e}")

    def _get_authenticity_token(self) -> str | None:
        """Fetch the login page and scrapes the CSRF authenticity token.

        Returns:
        -------
            The authenticity token as a string, or None if not found.

        """
        try:
            _LOGGER.info("Fetching login page to retrieve authenticity token...")
            response = self.session.get(self._login_url, timeout=15)
            response.raise_for_status()
        except RequestException as e:
            _LOGGER.error(f"Failed to fetch login page: {e}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        token_tag = soup.find("input", {"name": "authenticity_token"})

        if not token_tag or "value" not in token_tag.attrs:
            _LOGGER.error("Could not find 'authenticity_token' input field.")
            return None

        _LOGGER.info("Authenticity token retrieved successfully.")
        return token_tag["value"]

    def _perform_login(self, authenticity_token: str) -> bool:
        """Post login credentials to the login URL.

        Args:
        ----
            authenticity_token: The CSRF token retrieved from the login page.

        Returns:
        -------
            True if the login was successful, False otherwise.

        """
        payload = {
            "authenticity_token": authenticity_token,
            "user[email]": self._username,
            "user[password]": self._password,
            "user[remember_me]": "1",
        }

        # Using a User-Agent header is good practice for web scraping
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Referer": self._login_url,
        }

        try:
            _LOGGER.info("Attempting to post login credentials...")
            response = self.session.post(
                self._login_url,
                data=payload,
                headers=headers,
                timeout=15,
                allow_redirects=False,
            )

            if response.status_code in [302, 303]:
                _LOGGER.info(
                    "Login successful. Redirected to %s", response.headers["Location"]
                )
                self._save_session_cookies()
                return True
            else:
                _LOGGER.error(f"Login failed with status code: {response.status_code}")
                # Log the response body for debugging, but don't save to a file.
                _LOGGER.debug(f"Login failure response content:\n{response.text}")
                return False

        except RequestException as e:
            _LOGGER.error(f"Login POST request failed: {e}")
            return False

    def authenticate(self) -> requests.Session | None:
        """Return an authenticated session either from cache or a new login.

        Returns:
        -------
            The authenticated requests.Session object on success, None on failure.

        """
        if self._load_session_cookies():
            return self.session

        _LOGGER.info("No valid cached session found. Performing a fresh login.")
        authenticity_token = self._get_authenticity_token()
        if not authenticity_token:
            return None

        if self._perform_login(authenticity_token):
            return self.session

        return None
