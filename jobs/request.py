import argparse
import json
import sys

import requests
import html2text
import urllib.parse

import jobs.utils.tampering
import impl.core


def run(parser: argparse.ArgumentParser, request_parser: argparse.ArgumentParser):
    http_options = request_parser.add_argument_group("HTTP OPTIONS")
    payload_options = request_parser.add_argument_group("PAYLOAD OPTIONS")
    general_options = request_parser.add_argument_group("GENERAL OPTIONS")

    # HTTP Options
    http_options.add_argument("-u", dest="url", required=True, help="Target URL")

    parameter = http_options.add_mutually_exclusive_group(required=True)
    parameter.add_argument("-p", dest="param", help="Name of the injected parameter.")
    parameter.add_argument("--json", dest="param_json", action="store_true", help="If set, inject the ")

    injecter = http_options.add_mutually_exclusive_group(required=True)
    injecter.add_argument("-i", dest="inject", help="Unencoded value to inject in parameter")
    injecter.add_argument("-I", dest="inject_file", help="Unencoded file to inject in parameter")

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

    args = RequestProgramData(parser.parse_args())
    do_job(args, args.payload)


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

        print(f'{word:<25} [Status: {res_code}, Size: {res_size}, Words: {words_count}, Lines: {lines_count}]')

        if args.is_verbose:
            print("\nResponse Headers:")
            print(response.headers)
            print("\nResponse Content:")
            if args.param_json:
                content = response.json()
                print(json.dumps(content, indent=2))
            else:
                print(content.replace("\n\n", "\n"))
    except Exception as e:
        print(f'[X] {e}')


class RequestProgramData(impl.core.HttpProgramData):
    def __init__(self, args):
        super().__init__(args)

        self.param = args.param
        self.param_json = args.param_json

        if args.inject is not None:
            self.payload = [args.inject]
        elif args.inject_file is not None:
            with open(args.inject_file, 'r') as f:
                self.payload = ['\n'.join(f.readlines())]
        else:
            # todo: ...
            pass

        self.tamper = jobs.utils.tampering.TamperingHandler(args.tamper)

        if self.method == "GET":
            if self.param_json:
                print(f"[ERROR] Cannot use '-X GET' with '--json'.")
                sys.exit(2)
            self.parsed_url = urllib.parse.urlparse(self.url)
            self.query_params = urllib.parse.parse_qs(self.parsed_url.query)
            if self.param not in self.query_params:
                self.query_params[self.param] = []
        else:
            self.parsed_url = self.url

    def inject_word(self, word):
        word = self.tamper.apply(word)
        body_data = self.body
        json_data = None
        updated_url = self.parsed_url
        if self.method == "GET":
            pu = self.parsed_url
            self.query_params[self.param] = [word]
            updated_query = urllib.parse.urlencode(self.query_params, doseq=True)
            updated_url = urllib.parse.urlunparse(
                (pu.scheme, pu.netloc, pu.path, pu.params, updated_query, pu.fragment))
        else:
            if self.param_json:
                json_data = json.loads(word)
            else:
                body_data[self.param] = word

        return updated_url, body_data, json_data

    def __str__(self):
        return f"{self.__class__.__name__}(" \
               f"{super().__str__()}" \
               f")"
