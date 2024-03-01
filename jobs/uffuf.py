import argparse
import binascii
import logging
import os
import queue
import sys
import threading

import colorama
import html2text
import pyfiglet
import requests
import urllib3

import impl.core
import impl.worker
import jobs.utils.filtering

print_lock = threading.Lock()

uffuf_version = "0.3.2-unstable-dev"

keyword_auto = "auto"

default_status_codes = "200-299,301,302,307,401,403,405,500"

# Add more as needed
# https://en.wikipedia.org/wiki/List_of_file_signatures
mimetypes_to_bytes = {
    "image/jpeg": binascii.unhexlify('FFD8FFEE'),
    "image/jpg": binascii.unhexlify('FFD8FFE0'),

    "image/png": binascii.unhexlify('89504E470D0A1A0A'),

    "image/gif": binascii.unhexlify('474946383761'),

    "application/pdf": binascii.unhexlify('255044462D'),
}


class UffufProgramData(impl.core.HttpProgramData):
    def __init__(self, args):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        args.is_info = True
        args.is_debug = False
        args.method = 'POST'
        args.nr = False
        super().__init__(args)

        self.param = args.param
        self.file = args.file
        self.format = args.format
        self.should_spoof = args.should_spoof

        if args.wordlist is not None:
            try:
                if ":" in args.wordlist:
                    [self.wordlist, keyword] = args.wordlist.split(":")
                    self.keyword = keyword
                else:
                    self.wordlist = args.wordlist
                    self.keyword = "FUZZ"

                with open(self.wordlist, 'r') as file:
                    args.words = file.readlines()
            except FileNotFoundError:
                print(f"Error: Wordlist '{self.wordlist}' not found.")
                sys.exit(1)
        else:
            args.words = [args.word]
            self.wordlist = '<word = ' + args.word + '>'
            self.keyword = "FUZZ"

        try:
            with open(self.file, 'rb') as file:
                self.file_content = file.read()
                if args.filetype == keyword_auto:
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(self.file)
                    if mime_type is None:
                        mime_type = "application/octet-stream"
                    self.filetype = mime_type
                else:
                    self.filetype = args.filetype
        except FileNotFoundError:
            print(f"Error: File to upload '{self.file}' not found.")
            sys.exit(1)

        # compute filename
        if args.filename == keyword_auto:
            self.filename = os.path.basename(self.file)
        else:
            self.filename = args.filename

        if self.keyword not in self.filename and self.keyword not in self.filetype:
            print(f'Error: The keyword "{self.keyword}" was not found in either the filename or the filetype.')
            sys.exit(2)

        self.matcher = jobs.utils.filtering.FilteringHandler(False, args.mc, args.ml, args.mr, args.ms, args.mw)
        self.filter = jobs.utils.filtering.FilteringHandler(True, args.fc, args.fl, args.fr, args.fs, args.fw)

        # Create a queue to hold words from the wordlist
        self.words_queue = queue.Queue()
        words = [word.strip() for word in args.words]
        for word in words:
            self.words_queue.put(word)

    # fixme: factorize code
    def parse_response_content(self, response):
        content = response.text
        if self.format == "html":
            content = html2text.html2text(content)
        res_size = int(response.headers.get('Content-Length') or 0)
        lines_count = len(content.splitlines())
        words_count = len(content.split())
        content = content.replace("\n\n", "\n")

        return content, lines_count, words_count, res_size


def run(parser : argparse.ArgumentParser, uffuf_parser : argparse.ArgumentParser):
    http_options = uffuf_parser.add_argument_group("HTTP OPTIONS")
    general_options = uffuf_parser.add_argument_group("GENERAL OPTIONS")
    matcher_options = uffuf_parser.add_argument_group("MATCHER OPTIONS")
    filter_options = uffuf_parser.add_argument_group("FILTER OPTIONS")
    input_options = uffuf_parser.add_argument_group("INPUT OPTIONS")

    # HTTP Options
    http_options.add_argument("-H", metavar="header", dest="headers", action="append", help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")
    http_options.add_argument("-u", dest="url", required=True, help="Target URL")
    http_options.add_argument("-d", dest="body", help="Request body data.")
    http_options.add_argument("-p", dest="param", help="Name of the file parameter.", required=True)
    http_options.add_argument("-F", dest="file", help="Path to the file to upload.", required=True)
    http_options.add_argument("-Fn", dest="filename", default=keyword_auto, help="Name of the file to upload (default: %(default)s).")
    http_options.add_argument("-Ft", dest="filetype", default=keyword_auto, help="MIME types tested with the file (default: %(default)s).")
    http_options.add_argument("--spoof", dest="should_spoof", action="store_true", help="Modify file contents to inject the MIME type.")

    # General Options
    general_options.add_argument('-k', dest='ssl_verify', default=True, action='store_false', help='Do not verify SSL certificates.')
    general_options.add_argument("-t", dest="threads", type=int, default=10, help="Number of concurrent threads (default: %(default)s)")
    general_options.add_argument("-v", dest="is_verbose", action="store_true", help="Verbose output")
    general_options.add_argument("-f", dest="format", default="html", choices=["raw", "html"], help="Output format (default=%(default)s).")

    # Matcher Options
    matcher_options.add_argument("-mc", metavar="mc", default=default_status_codes, help="Match HTTP status codes, or 'all' for everything (default: %(default)s)")
    matcher_options.add_argument("-ml", metavar="ml", help="Match amount of lines in response")
    matcher_options.add_argument("-mr", metavar="mr", help="Match regexp")
    matcher_options.add_argument("-ms", metavar="ms", help="Match HTTP response size")
    matcher_options.add_argument("-mw", metavar="mw", help="Match amount of words in response")

    # Filter Options
    filter_options.add_argument("-fc", metavar="fc", help="Filter HTTP status codes from response")
    filter_options.add_argument("-fl", metavar="fl", help="Filter by amount of lines in response")
    filter_options.add_argument("-fr", metavar="fr", help="Filter regexp")
    filter_options.add_argument("-fs", metavar="fs", help="Filter HTTP response size")
    filter_options.add_argument("-fw", metavar="fw", help="Filter by amount of words in response")

    # Input Options
    wordlist = input_options.add_mutually_exclusive_group(required = True)
    wordlist.add_argument("-w", dest="wordlist", help="Wordlist file path and (optional) keyword separated by colon. eg. '/path/to/wordlist:KEYWORD'")
    wordlist.add_argument("-W", dest="word", help="Word used instead of a wordlist.")

    # Handle shared data
    args = parser.parse_args()
    args = UffufProgramData(args)
    logging.info(f'{args}\n')

    print_uffuf_header(args)

    impl.worker.start_threads(execute_worker_task, args, args.words_queue)


def print_uffuf_header(args : UffufProgramData):
    print(f"""
        ________________________________________________

        {pyfiglet.figlet_format("File Upload Fuzz")}
            v{uffuf_version}
        ________________________________________________

            URL            ::=  {args.url}
            Wordlist       ::=  {args.wordlist}
            Threads        ::=  {args.threads}
            Header(s)      ::=  {args.headers}
            File           ::=  (name: {args.filename}, type: {args.filetype}, path: {args.file})""")

    for filter in [args.matcher, args.filter]:
        if filter.status_code is not None and filter.status_code != default_status_codes:
            print(f'        {filter.name:<14} ::=  Response status: {filter.status_code}')
        if filter.line_count is not None:
            print(f'        {filter.name:<14} ::=  Response lines: {filter.line_count}')
        if filter.word_count is not None:
            print(f'        {filter.name:<14} ::=  Response words: {filter.word_count}')
        if filter.size is not None:
            print(f'        {filter.name:<14} ::=  Response size: {filter.size}')

    print(f"""
        ________________________________________________
        """)


def execute_worker_task(args):
    """Worker function to consume links from the queue."""
    while True:
        word = args.words_queue.get()
        if word is None:
            break
        do_job(args, word)
        args.words_queue.task_done()


def do_job(args : UffufProgramData, word):
    contents = args.file_content
    filetype = args.filetype.replace(args.keyword, word)
    if args.should_spoof:
        if filetype in mimetypes_to_bytes:
            contents = mimetypes_to_bytes[filetype] + contents
        else:
            print(f'[WARN] Cannot spoof file: MIME type {filetype} is not supported.')

    files = {
        args.param: (
            args.filename.replace(args.keyword, word),
            contents, filetype
        )
    }

    logging.debug(f'[Testing Payload For {word}] ', files)
    try:
        response = requests.post(args.url, data=args.body, files=files, headers=args.headers,
                                 verify=args.ssl_verify, allow_redirects=args.allow_redirects)

        content, lines, words, res_size = args.parse_response_content(response)
        res_code = response.status_code
        if res_size is not None:
            res_size = int(res_size)

        # remove not matching or filtered
        if not args.matcher.is_valid(res_code, lines, content, res_size, words):
            return
        if not args.filter.is_valid(res_code, lines, content, res_size, words):
            return

        with print_lock:
            print(colorama.Fore.GREEN + '[+] ' + colorama.Style.BRIGHT, end="")
            print(f'{word:<25} [Status: {res_code}, Size: {res_size}, Words: {words}, Lines: {lines}]\x1b[0m')
            print(colorama.Fore.RESET)
            logging.info(f'\nResponse Headers: \n\n{response.headers}')
            logging.info(f'\nResponse Content: \n\n{content}')
    except Exception as e:
        print(f'{word:<25} [Error {e}]')

