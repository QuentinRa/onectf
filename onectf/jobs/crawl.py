import argparse
import copy
import logging
import queue
import re
import threading
import urllib.parse
import urllib.robotparser
import bs4
import colorama
import requests
import urllib3

import onectf.impl.core
import onectf.impl.worker
import onectf.jobs.utils.parser_utils

set_lock = threading.Lock()


def run(parser: argparse.ArgumentParser, crawl_parser: argparse.ArgumentParser):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http_options = crawl_parser.add_argument_group("HTTP OPTIONS")
    general_options = crawl_parser.add_argument_group("GENERAL OPTIONS")
    output_options = crawl_parser.add_argument_group("OUTPUT OPTIONS")

    http_options.add_argument('-u', dest='url', help='The target website URL.', required=True)
    http_options.add_argument('-L', dest='endpoints', default=None, help='Load gobuster output list of endpoints.')
    http_options.add_argument('-k', dest='ssl_verify', default=True, action='store_false',
                              help='Do not verify SSL certificates.')
    http_options.add_argument("-H", metavar="header", dest="headers", action="append",
                              help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")

    general_options.add_argument('-t', metavar='threads', dest='threads', default=10,
                                 help='Number of threads (default=%(default)s).')
    onectf.jobs.utils.parser_utils.add_verbose_options(general_options)

    output_options.add_argument('--external', dest='external', action='store_true',
                                help='Show external URLs in the list of URLs.')
    output_options.add_argument('--comments', dest='print_comments', action='store_true',
                                help='Display comments (experimental).')
    output_options.add_argument('--emails', dest='print_emails', action='store_true',
                                help='Display emails (experimental).')
    output_options.add_argument('-o', metavar='output', dest='output_file', help='Write the output to a file.')

    args = parser.parse_args()

    # patch args
    args = CrawlerProgramData(args)
    logging.debug(args)

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
        self.url = self.url if self.url.endswith('/') else self.url + '/'
        self.add_to_set(self.url)
        self.external = args.external

        # we don't want to crawl these pages
        self.crawl_url_filter_match = re.compile(
            '.*(css|woff|woff2|ttf|js|png|jpg|gif|jpeg|svg|mp4|mp3|webm|webp|ico|less|eot|otf|txt|mo|po|pot|psd)$')

        self.print_comments = args.print_comments
        self.print_emails = args.print_emails
        self.comments = set()
        self.emails = set()

        # Load known endpoints
        if args.endpoints:
            with open(args.endpoints, 'r') as f:
                for raw_endpoint in f.readlines():
                    raw_endpoint = raw_endpoint.split()[0]
                    self.add_to_set(self.url + raw_endpoint[1:])

        try:
            # Load robots.txt
            f = requests.get(self.url + 'robots.txt')
            if f.status_code != 200:
                raise Exception(f"File 'robots.txt' not found (code={f.status_code})")
            # Add it
            self.found_urls.add(self.url + 'robots.txt')
            logging.info(
                colorama.Fore.BLUE + '[+] ' + colorama.Style.BRIGHT + \
                f'Found robots.txt file.' + \
                colorama.Fore.RESET
            )
            logging.debug(
                colorama.Fore.BLUE + '[+] ' + colorama.Style.BRIGHT + \
                f'robots.txt:' + f.text + \
                colorama.Fore.RESET
            )
            # try to find interesting endpoints
            pattern = r'\/[a-zA-Z0-9_\-/.]+'
            for raw_endpoint in re.findall(pattern, f.text):
                if raw_endpoint and raw_endpoint != '/':
                    target = self.url + raw_endpoint.strip()[1:]
                    self.add_to_set(target)
                    logging.info(
                        colorama.Fore.BLUE + '[+] ' + colorama.Style.BRIGHT + \
                        f'Added {target} from robots.txt.' + \
                        colorama.Fore.RESET
                    )
        except Exception as e:
            logging.debug(
                colorama.Fore.RED + '[-] ' + colorama.Style.BRIGHT + \
                str(e) + \
                colorama.Fore.RESET
            )

    def add_to_set(self, url):
        if not url.startswith(self.url):
            # Index external URLs if requested
            if self.external:
                with set_lock:
                    self.found_urls.add(url)
            return

        with set_lock:
            # we need to explore it
            if url not in self.found_urls:
                self.found_urls.add(url)
                self.links.put(url)

    def __deepcopy__(self, memo):
        # Create a new instance of the class.
        cls = self.__class__
        new_obj = cls.__new__(cls)
        for key, value in self.__dict__.items():
            if key != 'links':
                setattr(new_obj, key, copy.deepcopy(value, memo))
        new_obj.links = queue.Queue()
        return new_obj


def do_job(args: CrawlerProgramData, url):
    root = url

    try:
        response = requests.get(url, data=args.body, headers=args.headers, cookies=args.cookies,
                                verify=args.ssl_verify, allow_redirects=args.allow_redirects)
    except Exception as e:
        print(f'[ERROR] Could not send request, reason={e}')
        # clear queue
        while not args.links.empty():
            args.links.get()
        return

    if response.status_code != 200:
        logging.info(
            colorama.Fore.RED + '[-] ' + colorama.Style.BRIGHT + \
            f'[{response.status_code}] Unable to access {url}' + \
            colorama.Fore.RESET
        )
        return
    else:
        logging.info(
            colorama.Fore.GREEN + '[+] ' + colorama.Style.BRIGHT + \
            f'Crawl {url}' + \
            colorama.Fore.RESET
        )

    if response.url != url:
        url = response.url
        with set_lock:
            # we need to explore it
            if url not in args.found_urls:
                logging.info(
                    colorama.Fore.BLUE + '[>] ' + colorama.Style.BRIGHT + \
                    f'Crawl {root} => Crawl {url}' + \
                    colorama.Fore.RESET
                )
                args.found_urls.add(url)
            else:
                logging.info(
                    colorama.Fore.YELLOW + '[x] ' + colorama.Style.BRIGHT + \
                    f'Crawl {root} => Already crawled.' + \
                    colorama.Fore.RESET
                )
                return

    soup = bs4.BeautifulSoup(response.content, 'html.parser')

    # Tags using href
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        # Should only be inside <a> link by design
        if href.startswith("mailto:"):
            if args.print_emails:
                with set_lock:
                    args.emails.update(href.split('mailto:')[1].strip())
        else:
            parse_href_link(args, root, url, href)

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
                with set_lock:
                    args.comments.add("<!-- " + comment + " -->")

    if args.print_emails:
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', soup.get_text())
        if emails:
            with set_lock:
                args.emails.update(emails)


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
    urls = sorted(args.found_urls, key=url_extension)
    comments = args.comments
    emails = args.emails

    # Format Data As String
    url_list = ''
    comments_list = '\n'.join(comments)
    email_list = '\n'.join(emails)

    # Highlight filters
    pattern = re.compile('.*(/|html|php|js|css)$')

    print(f'[*] Found {len(urls)} URLs.\n')

    print("Found the following URLs:\n")
    for url in urls:
        if not pattern.match(url) and "?" not in url:
            print(colorama.Fore.GREEN + '[!] ' + colorama.Style.BRIGHT, end="")
            print(f'Found suspicious URL {url}')
            print(colorama.Fore.RESET, end="")
            url_list += '[!] ' + url + '\n'
        else:
            print(f'[*] Found URL {url}')
            url_list += '[*] ' + url + '\n'

    if args.print_comments:
        print("\nFound the following comments:\n")
        print(comments_list)
        print()

    if args.print_comments:
        print("\nFound the following emails:\n")
        print(email_list)
        print()

    if args.output_file is not None:
        with open(args.output_file, 'w') as file:
            file.writelines(
                "URLS\n\n" + url_list + "\n" + \
                "COMMENTS\n\n" + comments_list + "\n" + \
                "EMAILS\n\n" + email_list + "\n"
            )
