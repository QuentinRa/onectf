#!/usr/bin/env python3
import argparse
import sys


def main():
    import onectf.impl.constants
    parser = argparse.ArgumentParser(description="onectf - CTFs utilities")
    parser.add_argument("-V", "--version", action="version", version=onectf.impl.constants.version, help="Show version information")

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

    print(f"onectf v{onectf.impl.constants.version}\n")

    if module == 'crawl':
        import onectf.jobs.crawl
        onectf.jobs.crawl.run(parser, command_crawl)
    elif module == 'axfr':
        import onectf.jobs.axfr
        onectf.jobs.axfr.run(parser, command_axfr)
    elif module == 'hosts':
        import onectf.jobs.hosts
        onectf.jobs.hosts.run(parser, command_host)
    elif module == 'fav':
        import onectf.jobs.fav
        onectf.jobs.fav.run(parser, command_fav)
    elif module == 'request':
        import onectf.jobs.request
        onectf.jobs.request.run(parser, command_request)
    elif module == 'uffuf':
        import onectf.jobs.uffuf
        onectf.jobs.uffuf.run(parser, command_uffuf)
    else:
        raise Exception("No such module:", module)


if __name__ == "__main__":
    main()
