#!/usr/bin/env python3
import argparse

import impl.constants
import impl.core
import impl.worker


def main():
    parser = argparse.ArgumentParser(description="My Program")
    parser.add_argument("-V", "--version", action="version", version=impl.constants.version, help="Show version information")

    commands_parser = parser.add_subparsers(title='module', dest='module', required=True)
    command_crawl = commands_parser.add_parser('crawl', help='Crawl a website using link between pages.')
    command_host = commands_parser.add_parser('hosts', help='Add or update IP and domain in /etc/hosts')
    command_fav = commands_parser.add_parser('fav', help='Get your favorite commands')

    args, remaining_args = parser.parse_known_args()

    print(f"onectf v{impl.constants.version}\n")

    if args.module == 'crawl':
        import jobs.crawl
        jobs.crawl.run(parser, command_crawl)
    elif args.module == 'hosts':
        import jobs.hosts
        jobs.hosts.run(parser, command_host)
    elif args.module == 'fav':
        import jobs.fav
        jobs.fav.run(parser, command_fav)
    else:
        raise Exception("Command not supported.")


if __name__ == "__main__":
    main()
