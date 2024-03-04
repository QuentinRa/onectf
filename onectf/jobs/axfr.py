import argparse
import queue
import dns.resolver

import onectf.impl.core
import onectf.impl.worker


def run(parser: argparse.ArgumentParser, axfr_parser: argparse.ArgumentParser):
    axfr_parser.add_argument('-D', dest='domain', help='The target domain.', required=True)
    axfr_parser.add_argument('-w', dest='wordlist', help='Wordlist of subdomains.', required=True)
    axfr_parser.add_argument('-t', metavar='threads', dest='threads', default=10, help='Number of threads (default=%(default)s).')
    axfr_parser.add_argument('-r', dest='resolver', help='IP address of the DNS server queried.', required=True)
    args = parser.parse_args()

    # Patch missing arguments
    args.is_info = True

    # patch args
    args = DNSProgramData(args)

    try:
        onectf.impl.worker.start_threads(execute_worker_task, args, args.words_queue)
    except KeyboardInterrupt:
        print()


def execute_worker_task(args):
    """Worker function to consume links from the queue."""
    while True:
        word = args.words_queue.get()
        if word is None:
            break
        do_job(args, word)
        args.words_queue.task_done()


class DNSProgramData(onectf.impl.core.BaseProgramData):
    def __init__(self, args):
        args.is_info = True
        args.is_debug = False
        super().__init__(args)

        # Create a queue to hold words from the wordlist
        with open(args.wordlist, 'r') as file:
            self.__words__ = file.readlines()
        self.words_queue = queue.Queue()
        words = [word.strip() for word in self.__words__]
        for word in words:
            self.words_queue.put(word)

        # Save parameters
        self.domain = args.domain
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = [args.resolver]


def do_job(args, word):
    target = word + '.' + args.domain
    for nameserver in args.resolver.nameservers:
        try:
            response = dns.query.xfr(nameserver, target)
            dns.zone.from_xfr(response)
            print(f'[*] Found valid subdomain {target} using {nameserver}')
        except dns.xfr.TransferError:
            pass
