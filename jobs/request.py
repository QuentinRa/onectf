import argparse

import requests
import html2text
import urllib.parse


def run(parser : argparse.ArgumentParser, request_parser : argparse.ArgumentParser):
    http_options = request_parser.add_argument_group("HTTP OPTIONS")
    payload_options = request_parser.add_argument_group("PAYLOAD OPTIONS")
    general_options = request_parser.add_argument_group("GENERAL OPTIONS")

    # HTTP Options
    http_options.add_argument("-u", dest="url", required=True, help="Target URL")
    http_options.add_argument("-p", dest="param", help="Name of the injected parameter.", required=True)
    http_options.add_argument("-i", dest="inject", help="Unencoded value to inject in parameter", required=True)
    http_options.add_argument("-X", dest="method", default="GET", help="HTTP Method (default=%(default)s)")
    http_options.add_argument("-H", metavar="header", dest="headers", action="append", help="Header 'Name: Value', separated by colon. Multiple -H flags are accepted.")
    http_options.add_argument("-d", dest="data", help="POST data.")

    # PAYLOAD Options
    payload_options.add_argument("--s2t", dest="space2tab", action="store_true", help="Convert all spaces to tabs.")

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
        'inject': args.inject,
        'is_verbose': args.is_verbose,
        'is_raw': args.is_raw,
        'allow_redirects': not args.nr
    })

    if args.space2tab:
        data.inject = data.inject.replace(' ', '<tab>')

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


def _do_clean_injected_word(word):
    word = word.replace("<tab>", "\u0009")
    word = word.replace("<q>", "\u0027")
    word = word.replace("<m>", "-")
    word = word.replace("<er>", "2>&1")
    return word


def do_job(args, word):
    word = _do_clean_injected_word(word)
    body_data = args.data
    if args.method == "GET":
        pu = args.parsed_url
        args.query_params[args.param] = [word]
        updated_query = urllib.parse.urlencode(args.query_params, doseq=True)
        updated_url = urllib.parse.urlunparse((pu.scheme, pu.netloc, pu.path, pu.params, updated_query, pu.fragment))
    else:
        updated_url = args.parsed_url
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
