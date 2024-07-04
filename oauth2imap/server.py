#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import argparse
import socket
import socketserver

from typing import Dict, Any

import oauth2imap
import oauth2imap.config
import oauth2imap.oauth2 as oauth2
import oauth2imap.imap as imap

logger = oauth2imap.logger


class ImapTCPHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        config = getattr(self.server, "config")

        provider = oauth2.get_upstream_provider(config)
        if not provider:
            return None

        logger.info("%s: new connection", self.client_address)

        up = imap.Upstream(provider["imap-endpoint"], 993)
        ds = imap.Downstream(self.client_address, self.rfile, self.wfile)

        imap.session(config, ds, up)

        logger.debug("%s: finish", self.client_address)


class ImapServer(socketserver.ForkingTCPServer):
    config: Dict[str, Any]

    def __init__(self, addr: Any, handler: Any):
        self.address_family = socket.AF_INET
        self.socket_type = socket.SOCK_STREAM
        self.allow_reuse_address = True

        super().__init__(addr, handler)


# pylint: disable-next=unused-argument
def main(cmdargs: argparse.Namespace) -> int:
    config = oauth2imap.config.read()

    if isinstance(config, oauth2imap.Error):
        logger.critical("%s", config.message)
        return oauth2imap.EX_FAILURE

    saddr = (config["downstream"]["server"], config["downstream"]["port"])

    try:
        with ImapServer(saddr, ImapTCPHandler) as server:
            server.config = config
            server.serve_forever()
    except KeyboardInterrupt:
        pass

    return oauth2imap.EX_SUCCESS
