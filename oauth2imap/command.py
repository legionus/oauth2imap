#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import argparse
import sys
import logging

import oauth2imap

logger = oauth2imap.logger


def cmd_server(cmdargs: argparse.Namespace) -> int:
    import oauth2imap.server
    return oauth2imap.server.main(cmdargs)


def cmd_tunnel(cmdargs: argparse.Namespace) -> int:
    import oauth2imap.tunnel
    return oauth2imap.tunnel.main(cmdargs)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-v", "--verbose",
                        dest="verbose", action='count', default=0,
                        help="print a message for each action.")
    parser.add_argument('-q', '--quiet',
                        dest="quiet", action='store_true', default=False,
                        help='output critical information only.')
    parser.add_argument("-V", "--version",
                        action='version',
                        help="show program's version number and exit.",
                        version=oauth2imap.__VERSION__)
    parser.add_argument("-h", "--help",
                        action='help',
                        help="show this help message and exit.")


def setup_parser() -> argparse.ArgumentParser:
    epilog = "Report bugs to authors."

    description = """\
The utility provides imap server proxying access to another imap server with
oauth2 authentication.
"""
    parser = argparse.ArgumentParser(
            prog="oauth2imap",
            formatter_class=argparse.RawTextHelpFormatter,
            description=description,
            epilog=epilog,
            add_help=False,
            allow_abbrev=True)

    add_common_arguments(parser)

    subparsers = parser.add_subparsers(dest="subcmd", help="")

    # oauth2imap server
    sp0_description = """\
The mode in which a downstream imap4 server is created with a different
authentication method for access.
"""
    sp0 = subparsers.add_parser("server",
                                description=sp0_description,
                                help=sp0_description,
                                epilog=epilog,
                                add_help=False)
    sp0.set_defaults(func=cmd_server)
    add_common_arguments(sp0)

    # oauth2imap tunnel
    sp1_description = """\
The mode of operation is when a session to upstream is created immediately and
commands are received from stdin and the result will be written to stdout.
"""
    sp1 = subparsers.add_parser("tunnel",
                                description=sp1_description,
                                help=sp1_description,
                                epilog=epilog,
                                add_help=False)
    sp1.set_defaults(func=cmd_tunnel)
    add_common_arguments(sp1)

    return parser


def setup_logger(cmdargs: argparse.Namespace) -> None:
    match cmdargs.verbose:
        case 0:
            level = logging.WARNING
        case 1:
            level = logging.INFO
        case _:
            level = logging.DEBUG

    if cmdargs.quiet:
        level = logging.CRITICAL

    oauth2imap.setup_logger(logger, level=level, fmt="[%(asctime)s] %(message)s")


def cmd() -> int:
    parser = setup_parser()
    cmdargs = parser.parse_args()

    setup_logger(cmdargs)

    if 'func' not in cmdargs:
        parser.print_help()
        return oauth2imap.EX_FAILURE

    ret: int = cmdargs.func(cmdargs)

    return ret


if __name__ == '__main__':
    sys.exit(cmd())
