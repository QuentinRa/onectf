import argparse
import queue
import threading

import requests
import html2text
import urllib.parse

import jobs.utils.tampering
import impl.core
import impl.worker

print_lock = threading.Lock()


def run(parser: argparse.ArgumentParser, request_parser: argparse.ArgumentParser):
    http_options = request_parser.add_argument_group("HTTP OPTIONS")
    payload_options = request_parser.add_argument_group("PAYLOAD OPTIONS")
    general_options = request_parser.add_argument_group("GENERAL OPTIONS")

    # HTTP Options
    http_options.add_argument("-u", dest="url", required=True, help="Target URL")
    http_options.add_argument("-p", dest="param", help="Name of the injected parameter.", required=True)

    injecter = http_options.add_mutually_exclusive_group(required=True)
    injecter.add_argument("-i", dest="inject", help="Unencoded value to inject in parameter.")
    injecter.add_argument("-I", dest="inject_file", help="Unencoded file to inject in parameter.")
    injecter.add_argument("-w", dest="inject_wordlist", help="Unencoded wordlist of values to inject in parameter.")

    http_options.add_argument("-X", dest="method", default="GET", help="HTTP Method (default=%(default)s)")
    http_options.add_argument("-H", metavar="header", dest="headers", action="append",
                              help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")
    http_options.add_argument("-d", dest="body", help="Request body data.")

    # PAYLOAD Options
    payload_options.add_argument("--tamper", dest="tamper", default="aliases",
                                 help="Comma separated list of payload transformations (default=%(default)s). "
                                      f"Example values are: {', '.join(jobs.utils.tampering.tamper_known_values)}, etc.")

    # General Options
    general_options.add_argument("--raw", dest="is_raw", action="store_true", help="Raw HTML output")
    general_options.add_argument("--nr", "--no-redirect", action="store_true",
                                 help="Don't follow the response redirection.")
    general_options.add_argument('-t', metavar='threads', dest='threads', default=10,
                                 help='Number of threads (default=%(default)s).')
    general_options.add_argument("-v", dest="is_verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Parse the payload
    use_threading = False
    if args.inject is not None:
        payload = [args.inject]
    elif args.inject_file is not None:
        with open(args.inject_file, 'r') as f:
            payload = ['\n'.join(f.readlines())]
    else:
        with open(args.inject_wordlist, 'r') as f:
            payload = f.readlines()
            use_threading = True

    # Handle shared data
    args = RequestProgramData(args)

    # Run
    if use_threading:
        args.words = queue.Queue()
        for word in payload:
            args.words.put(word.strip())
        impl.worker.start_threads(execute_worker_task, args, args.words)
    else:
        do_job(args, payload[0])


def execute_worker_task(args):
    """Worker function to consume links from the queue."""
    while True:
        word = args.words.get()
        if word is None:
            break
        do_job(args, word)
        args.words.task_done()


def do_job(args, word):
    (url, body_data, json_data) = args.inject_word(word)
    try:
        response = requests.request(args.method, url, data=body_data, headers=args.headers,
                                    allow_redirects=args.allow_redirects, json=json_data)
        content = response.text
        if not args.is_raw:
            content = html2text.html2text(content)

        res_code = response.status_code
        res_size = int(response.headers.get('Content-Length') or 0)
        lines_count = len(content.splitlines())
        words_count = len(content.split())

        with print_lock:
            print(f'{word:<25} [Status: {res_code}, Size: {res_size}, Words: {words_count}, Lines: {lines_count}]')

            if args.is_verbose:
                print("\nResponse Headers:")
                print(response.headers)
                print("\nResponse Content:")
                print(content.replace("\n\n", "\n"))
    except Exception as e:
        print(f'[X] {e}')


class RequestProgramData(impl.core.HttpProgramData):
    def __init__(self, args):
        super().__init__(args)

        self.param = args.param
        self.tamper = jobs.utils.tampering.TamperingHandler(args.tamper)

        if self.method == "GET":
            self.__pu = urllib.parse.urlparse(self.url)
            self.__query_params = urllib.parse.parse_qs(self.__pu.query)

    def inject_word(self, word):
        word = self.tamper.apply(word)
        body_data = self.body
        updated_url = self.url

        # Inject 'word' in URL or in Body
        if self.method == "GET":
            self.__query_params[self.param] = [word]
            updated_query = urllib.parse.urlencode(self.__query_params, doseq=True)
            updated_url = urllib.parse.urlunparse(
                (self.__pu.scheme, self.__pu.netloc, self.__pu.path, self.__pu.params, updated_query, self.__pu.fragment))
        else:
            body_data[self.param] = word

        return updated_url, body_data, None

    def __str__(self):
        return f"{self.__class__.__name__}(" \
               f"{super().__str__()}, " \
               f"Parameter={self.param}, " \
               f"Tamper={self.tamper}" \
               f")"
