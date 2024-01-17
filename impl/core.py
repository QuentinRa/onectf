class BaseProgramData:
    def __int__(self, args):
        # compute URL
        if args.url.startswith("http"):
            self.url = args.url
        else:
            # noinspection HttpUrlsUsage
            self.url = "http://" + args.url

