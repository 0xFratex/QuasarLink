# QuasarLink/fetcher.py
import logging
import requests
import time # For timing
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry 
from typing import Optional, List, Dict, Any

from .utils import get_wikipedia_page_url, RateLimiter, WIKIPEDIA_API_URL

logger = logging.getLogger("QuasarLink")

class WikipediaFetcher:
    def __init__(self,
                 user_agent: str = "QuasarLink/0.2 (https://github.com/your-org/QuasarLink; your-contact@example.com)",
                 retries: int = 3,
                 backoff_factor: float = 0.5,
                 request_delay: float = 1.0, 
                 timeout: int = 15):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        
        retry_strategy = Retry(
            total=retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"], 
            backoff_factor=backoff_factor, 
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.rate_limiter = RateLimiter(delay_seconds=request_delay)
        self.timeout = timeout
        logger.debug(f"Fetcher instance created: User-Agent='{user_agent}', Retries={retries}, Backoff={backoff_factor}, Delay={request_delay}s, Timeout={timeout}s")


    def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        self.rate_limiter.wait() 
        
        attempt = 0
        # The Retry logic in HTTPAdapter handles actual retries. This loop is more for logging context if needed.
        # For now, we rely on the adapter's logging or deeper urllib3 logging if enabled.
        # However, we can log the initial attempt.
        
        req_log_str = f"Requesting URL: {url}"
        if params:
            req_log_str += f" with params: {params}"
        logger.debug(req_log_str)
        
        start_time = time.monotonic()
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            duration = time.monotonic() - start_time
            logger.debug(f"Request to {response.url} completed in {duration:.4f}s, Status: {response.status_code}")
            response.raise_for_status() 
            return response
        except requests.exceptions.HTTPError as e:
            duration = time.monotonic() - start_time
            logger.error(f"HTTP error after {duration:.4f}s for {url} (Params: {params}): {e.response.status_code} {e.response.reason}")
        except requests.exceptions.ConnectionError as e:
            duration = time.monotonic() - start_time
            logger.error(f"Connection error after {duration:.4f}s for {url} (Params: {params}): {e}")
        except requests.exceptions.Timeout as e:
            duration = time.monotonic() - start_time
            logger.error(f"Timeout error after {duration:.4f}s for {url} (Params: {params}): {e}")
        except requests.exceptions.RequestException as e: 
            duration = time.monotonic() - start_time
            logger.error(f"General request error after {duration:.4f}s for {url} (Params: {params}): {e}")
        return None

    def fetch_page_html(self, title: str) -> Optional[str]:
        page_url = get_wikipedia_page_url(title)
        logger.info(f"Fetching HTML for page: '{title}' (URL: {page_url})")
        response = self._make_request(page_url)
        if response:
            logger.debug(f"Successfully fetched HTML for '{title}'. Content length: {len(response.text)} bytes.")
            return response.text
        else:
            logger.warning(f"Failed to fetch HTML for '{title}'.")
            return None

    def get_random_page_titles(self, count: int) -> List[str]:
        titles: List[str] = []
        if count <= 0:
            logger.warning("Requested 0 or negative random page titles. Returning empty list.")
            return titles
            
        logger.info(f"Fetching {count} random page titles via API ({WIKIPEDIA_API_URL})...")
        
        base_params = {
            "action": "query",
            "format": "json",
            "list": "random",
            "rnnamespace": "0", # Main article namespace
        }
        
        fetched_count = 0
        api_requests_made = 0
        while fetched_count < count:
            api_requests_made +=1
            current_batch_size = min(count - fetched_count, 500) 
            params = base_params.copy()
            params["rnlimit"] = current_batch_size
            
            logger.debug(f"API request {api_requests_made}: Fetching batch of {current_batch_size} random titles. (Total fetched so far: {fetched_count})")
            response = self._make_request(WIKIPEDIA_API_URL, params=params) 
            
            if response:
                try:
                    data = response.json()
                    random_pages_data = data.get("query", {}).get("random", [])
                    batch_titles = [page["title"] for page in random_pages_data if "title" in page]
                    
                    if not batch_titles and current_batch_size > 0:
                        logger.warning(f"API request {api_requests_made} returned no random titles in a batch of {current_batch_size}. Stopping random title fetch.")
                        break
                        
                    titles.extend(batch_titles)
                    fetched_count_before_unique = len(titles)
                    titles = list(dict.fromkeys(titles)) # Ensure uniqueness while preserving order
                    newly_added_unique = len(titles) - (fetched_count_before_unique - len(batch_titles))

                    fetched_count = len(titles) # Update fetched_count to reflect unique titles

                    logger.debug(f"API request {api_requests_made}: Received {len(batch_titles)} titles, {newly_added_unique} were new unique. Total unique so far: {fetched_count}")
                    
                    if fetched_count >= count: 
                        logger.debug(f"Reached desired count of {count} unique random titles.")
                        break

                except requests.exceptions.JSONDecodeError:
                    logger.error(f"API request {api_requests_made}: Failed to decode JSON response for random pages. Response text: {response.text[:200]}...")
                    break 
                except KeyError as e:
                    logger.error(f"API request {api_requests_made}: Unexpected JSON structure in random pages API response. Missing key: {e}. Data: {str(data)[:200]}...")
                    break
            else:
                logger.error(f"API request {api_requests_made}: Failed to fetch a batch of random page titles from API. No response object.")
                break 
        
        if not titles:
            logger.warning(f"Could not fetch any random page titles after {api_requests_made} API attempts.")
        
        final_titles = titles[:count] # Ensure we don't return more than requested if API over-delivers due to uniqueness logic
        logger.info(f"Finished fetching random titles. Total API requests: {api_requests_made}. Returning {len(final_titles)} unique random titles (requested {count}).")
        return final_titles


    def get_page_url_from_title(self, title: str) -> str: 
        return get_wikipedia_page_url(title)