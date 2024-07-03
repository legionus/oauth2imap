#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import argparse
import sys

import oauth2imap
import oauth2imap.config
import oauth2imap.imap as imap

logger = oauth2imap.logger


# pylint: disable-next=unused-argument
def main(cmdargs: argparse.Namespace) -> int:
    config = oauth2imap.config.read()

    if isinstance(config, oauth2imap.Error):
        logger.critical("%s", config.message)
        return oauth2imap.EX_FAILURE

    logger.info("new connection")

    try:
        up = imap.Upstream(config["upstream"]["server"], config["upstream"]["port"])
        ds = imap.Downstream("pipe", sys.stdin.buffer, sys.stdout.buffer)

        imap.session(config, ds, up)

    except KeyboardInterrupt:
        pass

    logger.debug("finish")

    return oauth2imap.EX_SUCCESS
