import os
import logging
import json
from dotenv import load_dotenv
from src.login_client import get_authenticated_session
from src.scraper import get_all_stories

# Configure root logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Main function to perform the full workflow: login, fetch all stories from API.
    """
    load_dotenv()

    LOGIN_URL = os.getenv("API_LOGIN_URL")
    API_BASE_URL = os.getenv("API_BASE_URL") 
    
    USERNAME = os.getenv("API_USERNAME")
    PASSWORD = os.getenv("API_PASSWORD")
    
    CHILD_ID = os.getenv("CHILD_ID")
    if not CHILD_ID:
        logging.critical("CHILD_ID environment variable is missing. Please set it in .env.")
        return

    # Define the base path for all downloads
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")

    if not all([LOGIN_URL, API_BASE_URL, USERNAME, PASSWORD]):
        logging.critical("Missing required environment variables. Check your .env file.")
        return

    authenticated_session = get_authenticated_session(
        login_url=LOGIN_URL,
        username=USERNAME,
        password=PASSWORD
    )

    if authenticated_session:
        logging.info("Authenticated session obtained successfully. Proceeding to fetch stories from API.")
        
        # Call the main scraping function, which will handle the downloads
        get_all_stories(authenticated_session, API_BASE_URL, CHILD_ID, DOWNLOAD_PATH)
        
    else:
        logging.error("Failed to authenticate.")

if __name__ == "__main__":
    main()