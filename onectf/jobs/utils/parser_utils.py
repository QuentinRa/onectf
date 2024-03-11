import argparse

import onectf.impl.constants


def add_filter_options(parser: argparse.ArgumentParser):
    # Matcher Options
    matcher_options = parser.add_argument_group("MATCHER OPTIONS")
    matcher_options.add_argument("-mc", metavar="mc", default=onectf.impl.constants.default_status_codes, help="Match HTTP status codes, or 'all' for everything (default: %(default)s)")
    matcher_options.add_argument("-ml", metavar="ml", help="Match amount of lines in response")
    matcher_options.add_argument("-mr", metavar="mr", help="Match regexp")
    matcher_options.add_argument("-ms", metavar="ms", help="Match HTTP response size")
    matcher_options.add_argument("-mw", metavar="mw", help="Match amount of words in response")

    # Filter Options
    filter_options = parser.add_argument_group("FILTER OPTIONS")
    filter_options.add_argument("-fc", metavar="fc", help="Filter HTTP status codes from response")
    filter_options.add_argument("-fl", metavar="fl", help="Filter by amount of lines in response")
    filter_options.add_argument("-fr", metavar="fr", help="Filter regexp")
    filter_options.add_argument("-fs", metavar="fs", help="Filter HTTP response size")
    filter_options.add_argument("-fw", metavar="fw", help="Filter by amount of words in response")


def add_verbose_options(parser: argparse.ArgumentParser|object):
    verbose = parser.add_mutually_exclusive_group()
    verbose.add_argument('-v', dest='is_info', action='store_true', help='Info verbosity level.')
    verbose.add_argument('-vv', dest='is_debug', action='store_true', help='Debug verbosity level.')
