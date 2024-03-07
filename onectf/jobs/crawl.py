import argparse
import queue
import re
import threading
import urllib.parse
import bs4
import colorama
import requests
import urllib3

import onectf.impl.core
import onectf.impl.worker

set_lock = threading.Lock()


def run(parser: argparse.ArgumentParser, crawl_parser: argparse.ArgumentParser):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    crawl_parser.add_argument('-u', dest='url', help='The target website URL.', required=True)
    crawl_parser.add_argument('-L', dest='endpoints', default=None, help='Load gobuster output list of endpoints.')
    crawl_parser.add_argument('-t', metavar='threads', dest='threads', default=10, help='Number of threads (default=%(default)s).')
    crawl_parser.add_argument('-o', metavar='output', dest='output_file', help='Write the output to a file.')
    crawl_parser.add_argument('-k', dest='ssl_verify', default=True, action='store_false', help='Do not verify SSL certificates.')
    crawl_parser.add_argument("-H", metavar="header", dest="headers", action="append", help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")
    crawl_parser.add_argument('--pc', '--print-comments', dest='print_comments', action='store_true', help='Display comments (experimental).')
    args = parser.parse_args()

    # patch args
    args = CrawlerProgramData(args)

    try:
        onectf.impl.worker.start_threads(execute_worker_task, args, args.links)
    except KeyboardInterrupt:
        print()
    finally:
        done(args)


def execute_worker_task(args):
    """Worker function to consume links from the queue."""
    while True:
        word = args.links.get()
        if word is None:
            break
        do_job(args, word)
        args.links.task_done()


class CrawlerProgramData(onectf.impl.core.HttpProgramData):
    def __init__(self, args):
        args.is_info = True
        args.is_debug = False
        args.method = 'GET'
        args.body = None
        args.nr = False
        super().__init__(args)

        self.output_file = args.output_file

        self.links = queue.Queue()  # what we didn't explore
        self.found_urls = set()  # what we found
        self.add_to_set(self.url)

        # Patch the URL to remove any file
        self.url = truncated_file_url(self.url)
        self.add_to_set(self.url)

        # we don't want to crawl these pages
        self.crawl_url_filter_match = re.compile(
            '.*(css|woff|woff2|ttf|js|png|jpg|gif|jpeg|svg|mp4|mp3|webm|webp|ico)$')

        self.print_comments = args.print_comments

        # Load known endpoints
        if args.endpoints:
            base = self.url if self.url.endswith('/') else self.url + '/'
            with open(args.endpoints, 'r') as f:
                for raw_endpoint in f.readlines():
                    raw_endpoint = raw_endpoint.split()[0]
                    self.add_to_set(base + raw_endpoint[1:])

    def add_to_set(self, url):
        if not url.startswith(self.url):
            return

        with set_lock:
            # we need to explore it
            if url not in self.found_urls:
                self.found_urls.add(url)
                self.links.put(url)


def do_job(args: CrawlerProgramData, url):
    root = url
    print(colorama.Fore.GREEN + '[+] ' + colorama.Style.BRIGHT, end="")
    print(f'[*] Crawl {url}')
    print(colorama.Fore.RESET)

    try:
        response = requests.get(url, data=args.body, headers=args.headers,
                                verify=args.ssl_verify, allow_redirects=args.allow_redirects)
    except Exception as e:
        print(f'[ERROR] Could not send request, reason={e}')
        # clear queue
        while not args.links.empty():
            args.links.get()
        return

    if response.status_code != 200:
        print(colorama.Fore.RED + '[+] ' + colorama.Style.BRIGHT, end="")
        print(f'[{response.status_code}] Unable to access {url}')
        print(colorama.Fore.RESET)
        return

    if response.url != url:
        url = response.url
        with set_lock:
            # we need to explore it
            if url not in args.found_urls:
                print(colorama.Fore.BLUE + '[+] ' + colorama.Style.BRIGHT, end="")
                print(f'[*] Crawl {root} => Crawl {url}')
                print(colorama.Fore.RESET)
                args.found_urls.add(url)
            else:
                print(colorama.Fore.YELLOW + '[+] ' + colorama.Style.BRIGHT, end="")
                print(f'[*] Crawl {root} => Already crawled.')
                print(colorama.Fore.RESET)
                return

    soup = bs4.BeautifulSoup(response.content, 'html.parser')

    # Tags using href
    for tag in soup.find_all('a', href=True):
        parse_href_link(args, root, url, tag['href'])

    # Tags using src
    for tag in soup.find_all(['img', 'script'], src=True):
        absolute_url = urllib.parse.urljoin(url, tag['src'])
        args.add_to_set(truncated_file_url(absolute_url))

    # Tags using onclick
    for tag in soup.find_all(attrs={"onclick": True}):
        onclick_value = tag['onclick']
        if 'location.href' in onclick_value:
            start_index = onclick_value.find("'") + 1
            end_index = onclick_value.rfind("'")
            href = onclick_value[start_index:end_index]
            parse_href_link(args, root, url, href)

    if args.print_comments:
        comments = soup.find_all(string=lambda text: isinstance(text, bs4.Comment))

        for comment in comments:
            comment = ' '.join(comment.split()).strip()
            if comment:
                print("<!--", comment, "-->")

        if len(comments) > 0:
            print()


def parse_href_link(args, root, url, href):
    if href.startswith("/"):
        url = root
    absolute_url = urllib.parse.urljoin(url, href)
    if not re.match(args.crawl_url_filter_match, absolute_url):
        args.add_to_set(truncate_link_url(absolute_url))
    else:
        args.add_to_set(truncated_file_url(absolute_url))


def url_extension(url):
    parts = url.split('.')
    return parts[-1].lower() if len(parts) > 1 else ''


def truncated_file_url(url):
    """
    Remove the file and any anchor.
    """
    parsed_url = urllib.parse.urlparse(url)
    path_without_file = '/'.join(parsed_url.path.split('/')[:-1]) + '/'
    return urllib.parse.urlunparse((parsed_url.scheme, parsed_url.netloc, path_without_file, parsed_url.params, '', ''))


def truncate_link_url(url):
    """
    Remove any anchor.
    """
    parsed_url = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, '', ''))


def done(args):
    urls = args.found_urls
    pattern = re.compile('.*(/|html|php|js|css)$')
    print(f'[*] Found {len(urls)} URLs.')
    print()
    sorted_urls = sorted(urls, key=url_extension)
    for url in sorted_urls:
        if not pattern.match(url) and "?" not in url:
            print(f'[*] Found suspicious URL {url}')

    if args.output_file is not None:
        with open(args.output_file, 'w') as file:
            file.writelines('\n'.join(sorted_urls))
