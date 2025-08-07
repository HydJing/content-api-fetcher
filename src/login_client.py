import requests
import logging
import time
import json
from pathlib import Path
from typing import Dict, Optional
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# Configure logging for this module
logger = logging.getLogger(__name__)

# Define a path for the session cache file
SESSION_CACHE_PATH = Path("login_session_cache.json")
# Define the expiration time for the session cache in seconds (e.g., 1 day)
SESSION_EXPIRATION_SECONDS = 86400

def _save_session_cookies(session: requests.Session):
    """Saves the session's cookies to a cache file."""
    cookies = {
        'cookies': session.cookies.get_dict(),
        'created_at': time.time()
    }
    try:
        with open(SESSION_CACHE_PATH, "w") as f:
            json.dump(cookies, f)
        logger.info("Session cookies saved to cache.")
    except (IOError, TypeError) as e:
        logger.error(f"Failed to save session cache: {e}")

def _load_session_cookies() -> Optional[requests.Session]:
    """Loads cookies from the cache if they are not expired."""
    if not SESSION_CACHE_PATH.exists():
        return None

    try:
        with open(SESSION_CACHE_PATH, "r") as f:
            cookies_data = json.load(f)
        
        created_at = cookies_data.get('created_at')
        if not created_at or (time.time() - created_at) > SESSION_EXPIRATION_SECONDS:
            logger.info("Cached session has expired. Deleting cache.")
            SESSION_CACHE_PATH.unlink(missing_ok=True)
            return None

        session = requests.Session()
        session.cookies.update(cookies_data['cookies'])
        logger.info("Authenticated session loaded from cache.")
        return session
    except (json.JSONDecodeError, KeyError, IOError) as e:
        logger.error(f"Error loading session cache: {e}. Deleting corrupted file.")
        SESSION_CACHE_PATH.unlink(missing_ok=True)
        return None

def login_to_website(
    login_url: str, username: str, password: str
) -> Optional[requests.Session]:
    """
    Performs a two-step login to a website that uses CSRF protection.
    It returns an authenticated requests Session object on success.
    """
    session = requests.Session()

    # Step 1: Get the login page and scrape the authenticity token
    try:
        logger.info("Fetching login page to retrieve authenticity token...")
        response = session.get(login_url, timeout=15)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Failed to fetch login page: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    token_tag = soup.find('input', {'name': 'authenticity_token'})
    
    if not token_tag or 'value' not in token_tag.attrs:
        logger.error("Could not find the 'authenticity_token' input field on the page.")
        return None
    
    authenticity_token = token_tag['value']
    logger.info("Authenticity token retrieved successfully.")
    
    # Step 2: Post the credentials and the token
    payload = {
        'authenticity_token': authenticity_token,
        'user[email]': username,
        'user[password]': password,
        'user[remember_me]': '1'
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Referer": login_url
    }
    
    try:
        logger.info("Attempting to post login credentials...")
        response = session.post(login_url, data=payload, headers=headers, timeout=15, allow_redirects=False)
        
        if response.status_code in [302, 303]:
            logger.info("Login successful. Redirected to %s", response.headers['Location'])
            _save_session_cookies(session) # Save cookies on successful login
            return session
        else:
            logger.error(f"Login failed with status code: {response.status_code}")
            # --- START OF DEBUGGING CODE ---
            with open("login_failure_response.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info("Login response saved to 'login_failure_response.html' for inspection.")
            # --- END OF DEBUGGING CODE ---
            return None
    
    except RequestException as e:
        logger.error(f"Login POST request failed: {e}")
        return None

def get_authenticated_session(login_url: str, username: str, password: str) -> Optional[requests.Session]:
    """
    Returns an authenticated session, either by loading from cache or by performing a new login.
    """
    session = _load_session_cookies()
    if session:
        logger.info("Using existing authenticated session from cache.")
        return session
    
    logger.info("No valid cached session found. Performing a fresh login.")
    return login_to_website(login_url, username, password)