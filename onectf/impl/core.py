import logging
import colorama
import sys

import onectf.utils.filtering


class BaseProgramData:
    def __init__(self, args):
        self.threads = args.threads
        if args.is_info:
            self.verbosity = logging.INFO
        elif args.is_debug:
            self.verbosity = logging.DEBUG
        else:
            self.verbosity = logging.WARNING

        logging.basicConfig(level=self.verbosity, format='%(message)s', stream=sys.stdout)
        colorama.init()

    def __str__(self):
        return f"Verbose={logging.getLevelName(self.verbosity)}, " \
               f"Threads={self.threads}"


class HttpProgramData(BaseProgramData):
    def __init__(self, args):
        """
        Http program data handles the URL, the request body and headers.
        :param args:
        """
        super().__init__(args)

        if args.url.startswith("http"):
            self.url = args.url
        else:
            self.url = "http://" + args.url

        self.method = args.method

        self.headers = {}
        self.cookies = {}
        for header in args.headers or []:
            parts = header.split(":")
            header_name = parts[0].strip()
            if header_name == "Cookie":
                parts = parts[1].strip().split("=")
                self.cookies[parts[0].strip()] = '='.join(parts[1:]).strip()
            else:
                self.headers[parts[0].strip()] = parts[1].strip()

        if args.body:
            self.body = {k: v for k, v in [pair.split('=') for pair in args.body.split('&')]}
        else:
            self.body = {}

        self.ssl_verify = args.ssl_verify
        self.allow_redirects = not args.nr

    def __str__(self):
        return f"{super().__str__()}, " \
               f"URL={self.url}, " \
               f"Method={self.method}, " \
               f"Headers={self.headers}, " \
               f"Cookies={self.cookies}, " \
               f"Body={self.body}, " \
               f"SSL Verify={self.ssl_verify}, " \
               f"Follow Redirects={self.allow_redirects}"


class HttpProgramDataWithFilters(HttpProgramData):
    def __init__(self, args):
        super().__init__(args)
        self.matcher = onectf.utils.filtering.FilteringHandler(False, args.mc, args.ml, args.mr, args.ms, args.mw)
        self.filter = onectf.utils.filtering.FilteringHandler(True, args.fc, args.fl, args.fr, args.fs, args.fw)
