import argparse
import json
import logging
import queue
import sys
import threading

import colorama
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
    output_options = request_parser.add_argument_group("OUTPUT OPTIONS")

    # HTTP Options
    http_options.add_argument("-u", dest="url", required=True, help="Target URL")
    parameter = http_options.add_mutually_exclusive_group(required=True)
    parameter.add_argument("-p", dest="param", help="Name of the injected parameter.")
    parameter.add_argument("--fuzz", dest="use_fuzzing", help="Use fuzzing instead of parameter injection.", action="store_true")
    parameter.add_argument("--json", dest="use_json", help="Send payload as JSON in the request body.", action="store_true")
    parameter.add_argument("--raw", dest="use_raw", help="Send payload in the request body.", action="store_true")

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


    # OUTPUT Options
    output_options.add_argument("-f", dest="format", default="html", choices=["raw", "html", "json"], help="Output format (default=%(default)s).")


    # General Options
    general_options.add_argument("--nr", "--no-redirect", action="store_true",
                                 help="Don't follow the response redirection.")
    general_options.add_argument('-t', metavar='threads', dest='threads', default=10,
                                 help='Number of threads (default=%(default)s).')
    verbose = general_options.add_mutually_exclusive_group()
    verbose.add_argument('-v', dest='is_info', action='store_true', help='Info verbosity level.')
    verbose.add_argument('-vv', dest='is_debug', action='store_true', help='Debug verbosity level.')

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
    logging.info(f'{args}\n')

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
    (url, headers, body_data, json_data) = args.inject_word(word)
    word = word.replace('\n', '\\n')
    try:
        response = requests.request(args.method, url, data=body_data, headers=headers,
                                    allow_redirects=args.allow_redirects, json=json_data)
        logging.debug(f'\nHTTP {url}, Body: {body_data}, JSON: {json_data}\n')
        content, lines, words = args.parse_response_content(response)
        res_code = response.status_code
        res_size = int(response.headers.get('Content-Length') or 0)

        with print_lock:
            print(colorama.Fore.GREEN + '[+] ' + colorama.Style.BRIGHT, end="")
            print(f'{word:<25} [Status: {res_code}, Size: {res_size}, Words: {words}, Lines: {lines}]\x1b[0m')
            print(colorama.Fore.RESET)
            logging.info(f'\nResponse Headers: \n\n{response.headers}')
            logging.info(f'\nResponse Content: \n\n{content}')
    except Exception as e:
        logging.error(f'[ERROR] {e}')


class RequestProgramData(impl.core.HttpProgramData):
    def __init__(self, args):
        super().__init__(args)

        self.tamper = jobs.utils.tampering.TamperingHandler(args.tamper)
        self.format = args.format

        self.use_fuzzing = args.use_fuzzing
        self.use_json = args.use_json
        self.use_raw = args.use_raw
        if self.use_fuzzing:
            self.param = 'FUZZ'
            self.fuzzing_source = None
            if "FUZZ" in self.url:
                self.fuzzing_source = 'URL'
            elif "FUZZ" in self.body:
                self.fuzzing_source = 'BODY'
            else:
                for k, v in self.headers.items():
                    if 'FUZZ' in v:
                        self.fuzzing_source = k
                        break

            if self.fuzzing_source is None:
                logging.error(f'[ERROR] FUZZ keyword not found (checked URL, Body, Headers).')
                sys.exit(2)
        elif self.use_json:
            self.param = '<none>'
            if self.method == 'GET':
                print(f"[ERROR] Cannot use '-X GET' with '--json'.")
                sys.exit(2)
        elif self.use_raw:
            self.param = '<none>'
            if self.method == 'GET':
                print(f"[ERROR] Cannot use '-X GET' with '--raw'.")
                sys.exit(2)
            if self.body != {}:
                print(f"[ERROR] Cannot use '-d' with '--raw'.")
                sys.exit(2)
        else:
            self.param = args.param
            if self.method == "GET":
                self.__pu = urllib.parse.urlparse(self.url)
                self.__query_params = urllib.parse.parse_qs(self.__pu.query)

    def inject_word(self, word):
        word = self.tamper.apply(word)
        body_data = self.body
        updated_url = self.url
        json_data = None
        headers = self.headers

        # Inject 'word' in URL or in Body
        if self.use_fuzzing:
            if "URL" == self.fuzzing_source:
                updated_url = updated_url.replace("FUZZ", word)
            elif "BODY" == self.fuzzing_source:
                body_data[self.param] = word
            else:
                headers = self.headers
                headers[self.fuzzing_source] = headers[self.fuzzing_source].replace("FUZZ", word)
        elif self.use_json:
            json_data = json.loads(word)
        elif self.use_raw:
            body_data = word
        else:
            if self.method == "GET":
                self.__query_params[self.param] = [word]
                updated_query = urllib.parse.urlencode(self.__query_params, doseq=True)
                updated_url = urllib.parse.urlunparse(
                    (self.__pu.scheme, self.__pu.netloc, self.__pu.path, self.__pu.params, updated_query,
                     self.__pu.fragment))
            else:
                body_data[self.param] = word

        return updated_url, headers, body_data, json_data

    def parse_response_content(self, response):
        if self.format == "json" and response.text != '':
            content = json.dumps(response.json(), indent=2)
            return content, len(content.splitlines()), len(content.split())

        content = response.text
        if self.format == "html":
            content = html2text.html2text(content)
        lines_count = len(content.splitlines())
        words_count = len(content.split())
        content = content.replace("\n\n", "\n")

        return content, lines_count, words_count

    def __str__(self):
        return f"{self.__class__.__name__}(" \
               f"{super().__str__()}, " \
               f"Parameter={self.param}, " \
               f"Tamper={self.tamper}" \
               f")"
