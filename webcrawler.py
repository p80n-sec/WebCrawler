import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from concurrent.futures import ThreadPoolExecutor
import argparse
import logging
import threading

class WebCrawler:
    def __init__(self, base_url, session_token=None, allow_methods=['GET'], strip_params=False, max_depth=3, threads=5):
        self.base_url = base_url
        self.session_token = session_token
        self.allow_methods = allow_methods
        self.strip_params = strip_params
        self.max_depth = max_depth
        self.visited_urls = set()
        self.lock = threading.Lock()

        self.headers = {
            'User-Agent': 'Crawler/1.0',
        }
        if session_token:
            key, value = session_token.split('=')
            self.headers[key] = value

        logging.basicConfig(filename='p80ncrawler.log', level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')

        self.executor = ThreadPoolExecutor(max_workers=threads)

    def fetch_url(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logging.error(f"Error fetching {url}: {e}")
            return None

    def parse_links(self, html, current_url):
        soup = BeautifulSoup(html, 'html.parser')
        links = set()

        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(current_url, href)
            if self.strip_params:
                parsed_url = urlparse(full_url)
                full_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            links.add(full_url)
        return links

    def crawl(self, url=None, depth=0):
        if not url:
            url = self.base_url

        if url in self.visited_urls or depth > self.max_depth:
            return

        with self.lock:
            self.visited_urls.add(url)

        logging.info(f"Crawling: {url} at depth {depth}")
        html = self.fetch_url(url)
        if not html:
            return

        links = self.parse_links(html, url)

        for link in links:
            if urlparse(link).scheme in ['http', 'https']:
                self.executor.submit(self.crawl, link, depth + 1)

    def strip_request_body_params(self, request_body):
        if self.strip_params:
            parsed_body = parse_qs(request_body)
            stripped_body = {k: '' for k in parsed_body}
            return urlencode(stripped_body)
        return request_body

    def test_request(self, url, method='GET', request_body=None):
        if method not in self.allow_methods:
            logging.warning(f"Method {method} is not allowed.")
            return None

        headers = self.headers.copy()
        request_body = self.strip_request_body_params(request_body)

        if method == 'GET':
            return requests.get(url, headers=headers)
        elif method == 'POST':
            return requests.post(url, data=request_body, headers=headers)
        # Implement other HTTP methods if needed

def main():
    parser = argparse.ArgumentParser(description="Web Cache Deception Crawler")
    parser.add_argument('base_url', help='Base URL to start crawling from')
    parser.add_argument('--session-token', help='Session token to use (e.g., "siteSession=abc123")')
    parser.add_argument('--allow-methods', nargs='+', default=['GET'], help='Allowed HTTP methods (default: GET)')
    parser.add_argument('--strip-params', action='store_true', help='Strip parameters from URLs and request bodies')
    parser.add_argument('--max-depth', type=int, default=3, help='Maximum crawl depth (default: 3)')
    parser.add_argument('--threads', type=int, default=5, help='Number of threads for concurrent crawling (default: 5)')
    args = parser.parse_args()

    crawler = WebCrawler(
        base_url=args.base_url,
        session_token=args.session_token,
        allow_methods=args.allow_methods,
        strip_params=args.strip_params,
        max_depth=args.max_depth,
        threads=args.threads
    )

    crawler.crawl()

if __name__ == "__main__":
    main()
