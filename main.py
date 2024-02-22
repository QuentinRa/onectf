#!/usr/bin/env python3
import argparse
import sys

import impl.constants
import impl.core
import impl.worker


def main():
    parser = argparse.ArgumentParser(description="My Program")
    parser.add_argument("-V", "--version", action="version", version=impl.constants.version, help="Show version information")

    commands_parser = parser.add_subparsers(title='module', dest='module', required=True)
    command_crawl = commands_parser.add_parser('crawl', help='Crawl a website using link between pages.')
    command_axfr = commands_parser.add_parser('axfr', help='Explore a DNS using AXFR.')
    command_host = commands_parser.add_parser('hosts', help='Add or update IP and domain in /etc/hosts')
    command_fav = commands_parser.add_parser('fav', help='Get your favorite commands')
    command_request = commands_parser.add_parser('request', help="CLI Request Encoder")
    command_uffuf = commands_parser.add_parser('uffuf', help="Unrestricted File Upload Fuzzer")

    module = sys.argv[1] if len(sys.argv) >= 2 else None
    if module is None or module in ["-V", "-h"]:
        parser.parse_known_args()

    print(f"onectf v{impl.constants.version}\n")

    if module == 'crawl':
        import jobs.crawl
        jobs.crawl.run(parser, command_crawl)
    if module == 'axfr':
        import jobs.axfr
        jobs.axfr.run(parser, command_axfr)
    elif module == 'hosts':
        import jobs.hosts
        jobs.hosts.run(parser, command_host)
    elif module == 'fav':
        import jobs.fav
        jobs.fav.run(parser, command_fav)
    elif module == 'request':
        import jobs.request
        jobs.request.run(parser, command_request)
    elif module == 'uffuf':
        import jobs.uffuf
        jobs.uffuf.run(parser, command_uffuf)
    else:
        raise Exception("Command not supported.")


if __name__ == "__main__":
    main()
