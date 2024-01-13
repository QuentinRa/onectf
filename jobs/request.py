import argparse

import requests
import html2text
import urllib.parse

import jobs.utils.tampering


def run(parser : argparse.ArgumentParser, request_parser : argparse.ArgumentParser):
    http_options = request_parser.add_argument_group("HTTP OPTIONS")
    payload_options = request_parser.add_argument_group("PAYLOAD OPTIONS")
    general_options = request_parser.add_argument_group("GENERAL OPTIONS")

    # HTTP Options
    http_options.add_argument("-u", dest="url", required=True, help="Target URL")
    http_options.add_argument("-p", dest="param", help="Name of the injected parameter.", required=True)
    injecter = http_options.add_mutually_exclusive_group(required=True)
    injecter.add_argument("-i", dest="inject", help="Unencoded value to inject in parameter")
    injecter.add_argument("-I", dest="inject_file", help="Unencoded file to inject in parameter")

    http_options.add_argument("-X", dest="method", default="GET", help="HTTP Method (default=%(default)s)")
    http_options.add_argument("-H", metavar="header", dest="headers", action="append", help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")
    http_options.add_argument("-d", dest="data", help="POST data.")

    # PAYLOAD Options
    payload_options.add_argument("--s2t", dest="space2tab", action="store_true", help="Convert all spaces to tabs.")
    payload_options.add_argument("--tamper", dest="tamper", default="aliases", help="Comma separated list of payload transformations (default=%(default)s).")

    # General Options
    general_options.add_argument("--raw", dest="is_raw", action="store_true", help="Raw HTML output")
    general_options.add_argument("--nr", "--no-redirect", action="store_true", help="Don't follow the response redirection.")
    general_options.add_argument("-v", dest="is_verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    args = verify_arguments(args)
    do_job(args, args.inject)


def verify_arguments(args):
    data = type('ProgramData', (), {
        'param': args.param,
        'method': args.method,
        'is_verbose': args.is_verbose,
        'is_raw': args.is_raw,
        'allow_redirects': not args.nr
    })

    if args.inject is not None:
        data.inject = args.inject
    else:
        with open(args.inject_file, 'r') as f:
            data.inject = '\n'.join(f.readlines())

    data.tamper = jobs.utils.tampering.TamperingHandler(args.tamper)

    # compute URL
    if args.url.startswith("http"):
        data.url = args.url
    else:
        # noinspection HttpUrlsUsage
        data.url = "http://" + args.url

    if data.method == "GET":
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
    updated_url = args.parsed_url
    if args.method == "GET":
        pu = args.parsed_url
        if args.tamper.encode_url():
            args.query_params[args.param] = [word]
            updated_query = urllib.parse.urlencode(args.query_params, doseq=True)
        else:
            updated_query = urllib.parse.urlencode(args.query_params, doseq=True)
            if updated_query != "":
                updated_query += "&"
            updated_query += args.param + "=" + word

        updated_url = urllib.parse.urlunparse((pu.scheme, pu.netloc, pu.path, pu.params, updated_query, pu.fragment))
        print(updated_url)
    else:
        body_data[args.param] = word

    try:
        response = requests.request(args.method, updated_url, data=body_data, headers=args.headers, allow_redirects=args.allow_redirects)

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
            print(content.replace("\n\n", "\n"))
    except Exception as e:
        print(f'[X] {e}')
