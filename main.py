"""A robust, object-oriented framework for API authentication and media downloading.

The main application is orchestrated by the `Application` class, which
handles configuration, authentication, and the scraping process in a
structured manner, following the Google Python Style Guide and best practices.
"""

import logging
import os

from requests.exceptions import RequestException

from src.auth import AuthClient
from src.scraper import StoryScraper

# Use a consistent logger for the entire application
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
_LOGGER = logging.getLogger(__name__)

# The import and load logic for python-dotenv is now at the top-level.
# This ensures environment variables are loaded before any classes
# or functions need to access them.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    _LOGGER.warning(
        "python-dotenv not installed. Assuming environment variables are set."
    )


class Config:
    """A class load and validate application configs from environment variables."""

    def __init__(self):
        """Initialize configuration by loading environment variables."""
        self.login_url = os.getenv("API_LOGIN_URL")
        self.api_base_url = os.getenv("API_BASE_URL")
        self.username = os.getenv("API_USERNAME")
        self.password = os.getenv("API_PASSWORD")
        self.child_id = os.getenv("CHILD_ID")
        self.download_path = os.getenv("DOWNLOAD_PATH")

    def validate(self) -> None:
        """Validate that all required configuration variables are present.

        Raises:
        ------
            ValueError: If a required environment variable is missing.

        """
        required_vars = {
            "API_LOGIN_URL": self.login_url,
            "API_BASE_URL": self.api_base_url,
            "API_USERNAME": self.username,
            "API_PASSWORD": self.password,
            "CHILD_ID": self.child_id,
            "DOWNLOAD_PATH": self.download_path,
        }
        for var_name, value in required_vars.items():
            if not value:
                _LOGGER.critical(f"Missing required environment variable: {var_name}")
                raise ValueError(f"Missing required environment variable: {var_name}")
        _LOGGER.info("Configuration validated successfully.")


class Application:
    """The main application class to orchestrate the entire workflow."""

    def __init__(self):
        """Initialize the application by loading configuration."""
        self.config = Config()

    def run(self) -> None:
        """Execute the full application workflow."""
        try:
            self.config.validate()

            auth_client = AuthClient(
                login_url=self.config.login_url,
                username=self.config.username,
                password=self.config.password,
            )
            authenticated_session = auth_client.authenticate()

            if authenticated_session:
                _LOGGER.info(
                    "Authenticated session obtained successfully."
                    "Proceeding to fetch stories from API."
                )

                # Create and run the scraper
                story_scraper = StoryScraper(
                    session=authenticated_session,
                    base_api_url=self.config.api_base_url,
                    child_id=self.config.child_id,
                )
                story_scraper.download_all_stories(self.config.download_path)
            else:
                _LOGGER.error("Failed to authenticate.")

        except (ValueError, RuntimeError, RequestException) as e:
            _LOGGER.critical(f"Application failed to run: {e}")
            return


def main():
    """Entry point for the application."""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
