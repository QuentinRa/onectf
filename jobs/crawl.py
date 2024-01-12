import argparse
import queue
import re
import threading
import urllib.parse
import bs4
import requests
import urllib3
import impl.worker

set_lock = threading.Lock()


def run(parser : argparse.ArgumentParser, crawl_parser : argparse.ArgumentParser):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    crawl_parser.add_argument('-u', dest='url', help='The target website URL.', required=True)
    crawl_parser.add_argument('-t', metavar='threads', dest='threads', default=10, help='Number of threads (default=%(default)s).')
    crawl_parser.add_argument('-o', metavar='output', dest='output_file', help='Write the output to a file.')
    crawl_parser.add_argument('-k', dest='ssl_verify', default=True, action='store_false', help='Write the output to a file.')
    crawl_parser.add_argument('--pc', '--print-comments', dest='print_comments', action='store_true', help='Display comments (experimental).')
    args = parser.parse_args()

    args.links = queue.Queue()  # what we didn't explore
    args.found_urls = set()     # what we found
    add_to_set(args, args.url)
    # we don't want to crawl these pages
    args.crawl_url_filter_match = re.compile('.*(css|js|png|jpg|gif)$')

    try:
        impl.worker.start_threads(execute_worker_task, args, args.links)
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


def do_job(args, url):
    root = url
    print(f'[*] Crawl {url}')

    try:
        response = requests.get(url, verify=args.ssl_verify, allow_redirects=True)
    except Exception as e:
        print(f'[ERROR] Could not send request, reason={e}')
        # clear queue
        while not args.links.empty():
            args.links.get()
        return


    if response.status_code != 200:
        print(f'[{response.status_code}] Unable to access {url}')
        return

    if response.url != url:
        url = response.url
        with set_lock:
            # we need to explore it
            if url not in args.found_urls:
                print(f'[*] Crawl {root} => Crawl {url}')
                args.found_urls.add(url)
            else:
                print(f'[*] Crawl {root} => Already crawled.')
                return

    soup = bs4.BeautifulSoup(response.content, 'html.parser')

    # Tags using href
    for tag in soup.find_all('a', href=True):
        parse_href_link(args, root, url, tag['href'])

    # Tags using src
    for tag in soup.find_all(['img', 'script'], src=True):
        absolute_url = urllib.parse.urljoin(url, tag['src'])
        add_to_set(args, truncated_file_url(absolute_url))

    # Tags using onclick
    for tag in  soup.find_all(attrs={"onclick": True}):
        onclick_value = tag['onclick']
        if 'location.href' in onclick_value:
            start_index = onclick_value.find("'") + 1
            end_index = onclick_value.rfind("'")
            href = onclick_value[start_index:end_index]
            parse_href_link(args, root, url, href)

    if args.print_comments:
        comments = soup.find_all(string=lambda text: isinstance(text, bs4.Comment))
        for comment in comments:
            comment = ' '.join(comment.split())
            if comment:
                print(comment)


def add_to_set(args, value):
    if not value.startswith(args.url):
        return

    with set_lock:
        # we need to explore it
        if value not in args.found_urls:
            args.found_urls.add(value)
            args.links.put(value)


def parse_href_link(args, root, url, href):
    if href.startswith("/"):
        url = root
    absolute_url = urllib.parse.urljoin(url, href)
    if not re.match(args.crawl_url_filter_match, absolute_url):
        add_to_set(args, truncate_link_url(absolute_url))
    else:
        add_to_set(args, truncated_file_url(absolute_url))


def url_extension(url):
    parts = url.split('.')
    return parts[-1].lower() if len(parts) > 1 else ''


def truncated_file_url(url):
    parsed_url = urllib.parse.urlparse(url)
    path_without_file = '/'.join(parsed_url.path.split('/')[:-1]) + '/'
    return urllib.parse.urlunparse((parsed_url.scheme, parsed_url.netloc, path_without_file, parsed_url.params, '', ''))


def truncate_link_url(url):
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
