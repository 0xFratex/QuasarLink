# QuasarLink/utils.py
import time
import re
from urllib.parse import urljoin, quote

WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/"
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php" # For API calls like random pages

def get_wikipedia_page_url(title: str) -> str:
    """Constructs a Wikipedia page URL from a title."""
    formatted_title = quote(title.replace(" ", "_"), safe='') # Ensure even slashes are quoted if not part of path
    return urljoin(WIKIPEDIA_BASE_URL, f"wiki/{formatted_title}")

def normalize_whitespace(text: str) -> str:
    """Replaces multiple whitespace characters with a single space and strips."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be a valid filename."""
    name = re.sub(r'[^\w\s-]', '', name).strip()
    name = re.sub(r'[-\s]+', '-', name)
    return name

class RateLimiter:
    def __init__(self, delay_seconds: float = 1.0):
        self.delay_seconds = delay_seconds
        self.last_call_time = 0

    def wait(self):
        current_time = time.monotonic()
        elapsed = current_time - self.last_call_time
        wait_time = self.delay_seconds - elapsed
        if wait_time > 0:
            time.sleep(wait_time)
        self.last_call_time = time.monotonic()