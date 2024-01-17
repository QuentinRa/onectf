class BaseProgramData:
    def __init__(self, args):
        self.is_verbose = args.is_verbose
        self.threads = args.threads

    def __str__(self):
        return f"Verbose={self.is_verbose}, " \
               f"Threads={self.threads}" \


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
        for header in args.headers or []:
            parts = header.split(":")
            args.headers[parts[0].strip()] = parts[1].strip()

        if args.body:
            self.body = {k: v for k, v in [pair.split('=') for pair in args.data.split('&')]}
        else:
            self.body = {}

        self.allow_redirects = not args.nr
        self.is_raw = args.is_raw

    def __str__(self):
        return f"{super().__str__()}, " \
               f"URL={self.url}, " \
               f"Method={self.method}, " \
               f"Headers={self.headers}, " \
               f"Body={self.body}, " \
               f"Is Raw={self.is_raw}, " \
               f"Follow Redirects={self.allow_redirects}"
