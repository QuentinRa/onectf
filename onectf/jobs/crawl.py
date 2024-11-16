import argparse
import json
import logging
import os.path
import re

import colorama
import scrapy
import scrapy.crawler
import urllib.parse
import threading

import onectf.impl.core
import onectf.impl.worker
import onectf.jobs.utils.parser_utils

set_lock = threading.Lock()


def run(parser: argparse.ArgumentParser, crawl_parser: argparse.ArgumentParser):
    http_options = crawl_parser.add_argument_group("HTTP OPTIONS")
    general_options = crawl_parser.add_argument_group("GENERAL OPTIONS")
    output_options = crawl_parser.add_argument_group("OUTPUT OPTIONS")

    http_options.add_argument('-u', dest='url', help='The target website URL.', required=True)
    http_options.add_argument('-L', dest='endpoints', default=None, help='Load gobuster output list of endpoints.')
    http_options.add_argument("-H", metavar="header", dest="headers", action="append",
                              help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")

    general_options.add_argument('-t', metavar='threads', dest='threads', default=10,
                                 help='Number of threads (default=%(default)s).')
    onectf.jobs.utils.parser_utils.add_verbose_options(general_options)

    output_options.add_argument('--external', dest='external', action='store_true',
                                help='Show external URLs in the list of URLs.')
    output_options.add_argument('--comments', dest='print_comments', action='store_true',
                                help='Display comments.')
    output_options.add_argument('--emails', dest='print_emails', action='store_true',
                                help='Display emails.')
    output_options.add_argument('-o', metavar='output', dest='output_file', help='Write the output to a file.')

    args = parser.parse_args()

    # patch args
    args = CrawlerProgramData(args)
    logging.debug(args)

    do_job(args)


class CrawlerProgramData(onectf.impl.core.HttpProgramData):
    def __init__(self, args):
        args.method = 'GET'
        args.body = None
        args.nr = False
        args.ssl_verify = False
        super().__init__(args)

        self.output_file = args.output_file
        self.start_urls = []
        self.start_urls.append(self.url)
        self.print_comments = args.print_comments
        self.print_emails = args.print_emails
        self.external = args.external

        # Load known endpoints
        if args.endpoints:
            base_endpoint = truncated_file_url(self.url)
            base_endpoint = base_endpoint if base_endpoint.endswith('/') else base_endpoint + '/'
            with open(args.endpoints, 'r') as f:
                for raw_endpoint in f.readlines():
                    raw_endpoint = raw_endpoint.split()[0]
                    self.start_urls.append(base_endpoint + raw_endpoint[1:])


def compute_absolute_url(response, link):
    parsed_link = urllib.parse.urlparse(link)
    if not parsed_link.scheme:
        link = response.urljoin(link)
        parsed_link = urllib.parse.urlparse(link)
    link = urllib.parse.urlunparse(parsed_link._replace(fragment=""))
    return link, not urllib.parse.urlparse(link).netloc == urllib.parse.urlparse(response.url).netloc


class CustomCrawler(scrapy.Spider):
    name = "CustomCrawler"

    def __init__(self, crawler_args: CrawlerProgramData, *args, **kwargs):
        super(CustomCrawler, self).__init__(*args, **kwargs)
        self.args = crawler_args
        self.email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.location_href_regex = re.compile(r'location\.href\s*=\s*[\'"]([^\'"]+)[\'"]')
        self.results = {
            'emails': set(),
            'links': set(),
            'external': set(),
            'comments': set(),
            'resources': {
                "css": set(),
                "js": set(),
                "pdf": set(),
                "images": set(),
            }
        }
        self.visited_urls = set()

    def start_requests(self):
        for url in self.args.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def add_result(self, external, absolute_url, truncated_url):
        if external:
            self.results['external'].add(absolute_url)
            return

        key_abs, key_trunc = 'links', 'links'
        root, ext = os.path.splitext(absolute_url)
        if ext:
            ext = ext[1:]
            if ext in ['png', 'jpg', 'gif']:
                ext = 'images'

        if ext and ext in self.results['resources']:
            self.results['resources'][ext].add(absolute_url)
            self.results[key_trunc].add(truncated_url)
            return

        self.results[key_abs].add(absolute_url)
        self.results[key_trunc].add(truncated_url)

    def parse(self, response, **kwargs):
        self.visited_urls.add(response.url)

        # Patch to skip files that we can't read
        # (we can still look for emails/etc. even if it's not a HTML file)
        if not response.headers.get('Content-Type', '').decode('utf-8').startswith('text'):
            return

        url = response.url
        logging.info(
            colorama.Fore.GREEN + '[+] ' + colorama.Style.BRIGHT + \
            f'Crawl {url}' + \
            colorama.Fore.RESET
        )

        # Parse links
        links = response.css('a::attr(href)').getall()
        for link in links:
            if link.startswith("mailto:"):
                continue
            absolute_url, external = compute_absolute_url(response, link)
            if not external and absolute_url not in self.visited_urls:
                self.visited_urls.add(response.url)
                yield response.follow(absolute_url, callback=self.parse)
            truncated_url = truncated_file_url(absolute_url)
            if not external and truncated_url not in self.visited_urls:
                self.visited_urls.add(response.url)
                yield response.follow(truncated_url, callback=self.parse)
            self.add_result(external, absolute_url, truncated_url)

        # Parse resource links
        links = response.css('link::attr(href), img::attr(src), script::attr(src), video::attr(src), '
                             'source::attr(src), audio::attr(src)').getall()
        for link in links:
            absolute_url, external = compute_absolute_url(response, link)
            if not external and absolute_url not in self.visited_urls:
                self.visited_urls.add(response.url)
                yield response.follow(absolute_url, callback=self.parse)
            truncated_url = truncated_file_url(absolute_url)
            if not external and truncated_url not in self.visited_urls:
                self.visited_urls.add(response.url)
                yield response.follow(truncated_url, callback=self.parse)
            self.add_result(external, absolute_url, truncated_url)

        # Parse dynamic links
        links = response.css('*::attr(onclick)').getall()
        for link in links:
            match = self.location_href_regex.match(link)
            if match:
                link = match[1]
                absolute_url, external = compute_absolute_url(response, link)
                if not external and absolute_url not in self.visited_urls:
                    self.visited_urls.add(response.url)
                    yield response.follow(absolute_url, callback=self.parse)
                truncated_url = truncated_file_url(absolute_url)
                if not external and truncated_url not in self.visited_urls:
                    self.visited_urls.add(response.url)
                    yield response.follow(truncated_url, callback=self.parse)
                self.add_result(external, absolute_url, truncated_url)

        # Parse emails
        if self.args.print_emails:
            emails = set(self.email_regex.findall(response.text))
            self.results['emails'].update(emails)

        # Parse comments
        if self.args.print_comments:
            comments = response.xpath('//comment()').getall()
            self.results['comments'].update(comments)

    def closed(self, reason):

        if not self.args.external:
            self.results['external'] = set()

        urls = list(self.results['external'])
        urls.extend(list(self.results['links']))
        urls = sorted(urls, key=url_extension)

        # Convert sets to lists for JSON serialization
        for key in self.results:
            value = self.results[key]
            if isinstance(value, set):
                self.results[key] = list(value)
            else:
                for _key in self.results[key]:
                    self.results[key][_key] = list(self.results[key][_key])

        if self.args.output_file is not None:
            with open(self.args.output_file, 'w') as f:
                json.dump(self.results, f, indent=4)

        comments = self.results['comments']
        emails = self.results['emails']
        url_list = ''
        comments_list = '\n'.join(comments)
        email_list = '\n'.join(emails)
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

        if self.args.print_comments:
            if comments_list.strip():
                print("\nFound the following comments:\n")
                print(comments_list)
            else:
                print("\nNo HTML comments.")

        if self.args.print_emails:
            print("\nFound the following emails:\n")
            print(email_list)


# Scrapy doesn't honor the given "settings"
# We need to use "install_root_handler" and use a custom handler
class ScrapyLoggingPatch(logging.StreamHandler):
    def emit(self, record):
        if record.name.startswith("scrapy."):
            return
        self.setLevel(record.levelno)
        return super().emit(record)


def url_extension(url):
    parts = url.split('.')
    return parts[-1].lower() if len(parts) > 1 else ''


def do_job(args: CrawlerProgramData):
    logging.getLogger().handlers = [ScrapyLoggingPatch()]
    process = scrapy.crawler.CrawlerProcess(settings={
        'CONCURRENT_REQUESTS': args.threads,
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7'
    }, install_root_handler=False)
    process.crawl(CustomCrawler, crawler_args=args)
    process.start()


def truncated_file_url(url):
    """
    Remove the file and any anchor.
    """
    parsed_url = urllib.parse.urlparse(url)
    path_without_file = '/'.join(parsed_url.path.split('/')[:-1]) + '/'
    return urllib.parse.urlunparse((parsed_url.scheme, parsed_url.netloc, path_without_file, parsed_url.params, '', ''))


def done(args):
    pass
