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

import onectf.impl.core
import onectf.impl.constants
import onectf.impl.worker
import onectf.jobs.utils.parser_utils
import onectf.utils.filtering
import onectf.utils.tampering

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
    http_options.add_argument("-H", metavar="header", dest="headers", action="append", help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")
    http_options.add_argument("-d", dest="body", help="Request body data.")

    # PAYLOAD Options
    payload_options.add_argument("--jsonp", dest="payload", help=f"Replace '{onectf.impl.constants.injection_token}' with 'word' before sending the JSON payload.")
    payload_options.add_argument("--tamper", dest="tamper", default="aliases",
                                 help="Comma separated list of payload transformations (default=%(default)s). "
                                      f"Example values are: {', '.join(onectf.utils.tampering.tamper_known_values)}, etc.")

    # Matcher and Filter Options
    onectf.jobs.utils.parser_utils.add_filter_options(request_parser)

    # OUTPUT Options
    output_options.add_argument("-f", dest="format", default="html", choices=["raw", "html", "json"], help="Output format (default=%(default)s).")
    output_options.add_argument("-o", dest="output", help="Path to a file to save the response content into.")

    # General Options
    general_options.add_argument('-k', dest='ssl_verify', default=True, action='store_false', help='Do not verify SSL certificates.')
    general_options.add_argument("--nr", "--no-redirect", action="store_true", help="Don't follow the response redirection.")
    general_options.add_argument('-t', metavar='threads', dest='threads', default=10, help='Number of threads (default=%(default)s).')
    onectf.jobs.utils.parser_utils.add_verbose_options(general_options)

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
        onectf.impl.worker.start_threads(execute_worker_task, args, args.words)
    else:
        do_job(args, payload[0])

    finish_job(args)


def execute_worker_task(args):
    """Worker function to consume links from the queue."""
    while True:
        word = args.words.get()
        if word is None:
            break
        do_job(args, word)
        args.words.task_done()


def do_job(args, word):
    (word, url, headers, cookies, body_data, json_data) = args.inject_word(word)
    word = word.replace('\n', '\\n')
    word = word.replace('\r', '\\r')
    try:
        response = requests.request(args.method, url, data=body_data, headers=headers, cookies=cookies,
                                    allow_redirects=args.allow_redirects, json=json_data, verify=args.ssl_verify)
        logging.debug(f'\nHTTP {url}, Body: {body_data}, JSON: {json_data}\n')
        content, lines, words = args.parse_response_content(response)
        res_code = response.status_code
        res_size = int(response.headers.get('Content-Length') or 0)

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

            args.results.append({
                "word": word,
                "status": res_code,
                "size": res_size,
                "words": words,
                "lines": lines,
                "headers": dict(response.headers),
                "content": content
            })
    except Exception as e:
        logging.error(f'[ERROR] {e}')


def finish_job(args):
    if args.output is not None:
        with open(args.output, 'w') as f:
            json.dump(args.results, f, indent=2)


class RequestProgramData(onectf.impl.core.HttpProgramDataWithFilters):
    def __init__(self, args):
        super().__init__(args)

        self.tamper = onectf.utils.tampering.TamperingHandler(args.tamper)
        self.format = args.format
        self.output = args.output

        self.use_fuzzing = args.use_fuzzing
        self.use_json = args.use_json
        self.use_raw = args.use_raw

        self.results = []

        self.payload = args.payload
        if self.use_fuzzing:
            self.param = 'FUZZ'
            self.fuzzing_source = None
            if "FUZZ" in self.url:
                self.fuzzing_source = 'URL'
            else:
                for source, items_dict in {'HEADERS': self.headers, 'COOKIES': self.cookies, 'BODY': self.body}.items():
                    for k, v in items_dict.items():
                        if 'FUZZ' in v:
                            self.fuzzing_source = source
                            self.param = k
                            break

            if self.fuzzing_source is None:
                logging.error(f'[ERROR] FUZZ keyword not found (checked URL, Body, Headers).')
                sys.exit(2)
        elif self.use_json:
            self.param = '<none>'
            if self.method == 'GET':
                logging.error(f"[ERROR] Cannot use '-X GET' with '--json'.")
                sys.exit(2)

            if self.payload is None or onectf.impl.constants.injection_token not in self.payload:
                logging.error(f"Payload must contains the placeholder '{onectf.impl.constants.injection_token}', e.g., {{\"name\": \"{onectf.impl.constants.injection_token}\"}}.")
                sys.exit(2)
        elif self.use_raw:
            self.param = '<none>'
            if self.method == 'GET':
                logging.error(f"[ERROR] Cannot use '-X GET' with '--raw'.")
                sys.exit(2)
            if self.body != {}:
                logging.error(f"[ERROR] Cannot use '-d' with '--raw'.")
                sys.exit(2)
        else:
            self.param = args.param
            if self.method == "GET":
                self.__pu = urllib.parse.urlparse(self.url)
                self.__query_params = urllib.parse.parse_qs(self.__pu.query)

        if not self.use_json and self.payload is not None:
            logging.warning(f'[WARNING] Ignored --payload as it is only supported with --json.')

    def inject_word(self, word):
        word = self.tamper.apply(word)
        body_data = self.body
        updated_url = self.url
        json_data = None
        headers = self.headers
        cookies = self.cookies

        # Inject 'word' in URL or in Body
        if self.use_fuzzing:
            if "URL" == self.fuzzing_source:
                updated_url = updated_url.replace("FUZZ", word)
            elif "BODY" == self.fuzzing_source:
                body_data = self.body.copy()
                body_data[self.param] = body_data[self.param].replace("FUZZ", word)
            elif "HEADERS" == self.fuzzing_source:
                headers = self.headers.copy()
                headers[self.param] = headers[self.param].replace("FUZZ", word)
            elif "COOKIES" == self.fuzzing_source:
                cookies = self.cookies.copy()
                cookies[self.param] = cookies[self.param].replace("FUZZ", word)
            else:
                raise Exception("Unexpected source:" + self.fuzzing_source)
        elif self.use_json:
            if self.payload is None:
                json_data = json.loads(word)
            else:
                payload = self.payload.replace(onectf.impl.constants.injection_token, word)
                json_data = json.loads(payload)
        elif self.use_raw:
            word = urllib.parse.unquote(word)
            body_data = word
        else:
            if self.method == "GET":
                self.__query_params[self.param] = [word]
                updated_query = urllib.parse.urlencode(self.__query_params, doseq=True)
                updated_url = urllib.parse.urlunparse(
                    (self.__pu.scheme, self.__pu.netloc, self.__pu.path, self.__pu.params, updated_query,
                     self.__pu.fragment))
            else:
                word = urllib.parse.unquote(word)
                body_data = self.body.copy()
                body_data[self.param] = word

        return word, updated_url, headers, cookies, body_data, json_data

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
