import argparse
import json
import sys

import requests
import html2text
import urllib.parse

import jobs.utils.tampering
from impl.core import BaseProgramData


def run(parser : argparse.ArgumentParser, request_parser : argparse.ArgumentParser):
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
    http_options.add_argument("-H", metavar="header", dest="headers", action="append", help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")
    http_options.add_argument("-d", dest="data", help="POST data.")

    # PAYLOAD Options
    payload_options.add_argument("--tamper", dest="tamper", default="aliases",
                                 help="Comma separated list of payload transformations (default=%(default)s). "
                                      f"Example values are: {', '.join(jobs.utils.tampering.tamper_known_values)}, etc.")

    # General Options
    general_options.add_argument("--raw", dest="is_raw", action="store_true", help="Raw HTML output")
    general_options.add_argument("--nr", "--no-redirect", action="store_true", help="Don't follow the response redirection.")
    general_options.add_argument('-t', metavar='threads', dest='threads', default=10, help='Number of threads (default=%(default)s).')
    general_options.add_argument("-v", dest="is_verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    args = verify_arguments(args)
    do_job(args, args.inject)


class RequestProgramData(BaseProgramData):
    def __init__(self, args):
        super().__init__(args)
    
        self.param = args.param
        self.param_json = args.param_json
        self.method = args.method
        self.is_verbose = args.is_verbose
        self.is_raw = args.is_raw
        self.allow_redirects = not args.nr

        if args.inject is not None:
            self.payload = [args.inject]
        elif args.inject_file is not None:
            with open(args.inject_file, 'r') as f:
                self.payload = ['\n'.join(f.readlines())]
        else:
            pass

        self.tamper = jobs.utils.tampering.TamperingHandler(args.tamper)


def verify_arguments(args):
    data = ProgramData(args)
    # compute URL
    if args.url.startswith("http"):
        data.url = args.url
    else:
        # noinspection HttpUrlsUsage
        data.url = "http://" + args.url

    if data.method == "GET":
        if data.param_json:
            print(f"[ERROR] Cannot use '-X GET' with '--json'.")
            sys.exit(2)
        data.parsed_url = urllib.parse.urlparse(data.url)
        data.query_params = urllib.parse.parse_qs(data.parsed_url.query)
        if data.param not in data.query_params:
            data.query_params[data.param] = []
    else:
        data.parsed_url = data.url

    # computer headers
    data.headers = {}
    for header in args.headers or []:
        parts = header.split(":")
        data.headers[parts[0].strip()] = parts[1].strip()

    if args.data:
        data.data = {k: v for k, v in [pair.split('=') for pair in args.data.split('&')]}
    else:
        data.data = {}

    return data


def do_job(args, word):
    word = args.tamper.apply(word)
    body_data = args.data
    json_data = None
    updated_url = args.parsed_url
    if args.method == "GET":
        pu = args.parsed_url
        args.query_params[args.param] = [word]
        updated_query = urllib.parse.urlencode(args.query_params, doseq=True)
        updated_url = urllib.parse.urlunparse((pu.scheme, pu.netloc, pu.path, pu.params, updated_query, pu.fragment))
    else:
        if args.param_json:
            json_data = json.loads(word)
        else:
            body_data[args.param] = word

    try:
        response = requests.request(args.method, updated_url, data=body_data, headers=args.headers,
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
