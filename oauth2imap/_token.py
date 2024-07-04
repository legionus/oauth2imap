#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import argparse
import socket
import secrets
import base64
import hashlib
import http.server
import urllib.parse
import urllib.request

from typing import Dict, Any

import oauth2imap
import oauth2imap.config
import oauth2imap.oauth2 as oauth2

logger = oauth2imap.logger

class HTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles the browser query resulting from redirect to redirect_uri."""

    # pylint: disable=C0103
    def do_HEAD(self) -> None:
        """Response to a HEAD requests."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self) -> None:
        """For GET request, extract code parameter from URL."""
        data = getattr(self.server, "data")

        querystring = urllib.parse.urlparse(self.path).query
        querydict = urllib.parse.parse_qs(querystring)

        if "code" in querydict:
            data["authcode"] = querydict["code"][0]

        self.do_HEAD()

        self.wfile.write(b"<html><head><title>Authorizaton result</title></head>")
        self.wfile.write(b"<body><p>Authorization redirect completed. You may "
                         b"close this window.</p></body></html>")


class HTTPServer(http.server.HTTPServer):
    data: Dict[str,str] = {}

    def __init__(self, addr: Any, handler: Any):
        self.data["authcode"] = ""
        super().__init__(addr, handler)


def get_localhost_authcode(port: int) -> str:
    with HTTPServer(("127.0.0.1", port), HTTPRequestHandler) as server:
        try:
            server.handle_request()
        except KeyboardInterrupt:
            pass
        return server.data["authcode"]
    return ""


def get_available_port() -> int:
    sock = socket.socket()

    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    return int(port)


# pylint: disable-next=unused-argument
def main(cmdargs: argparse.Namespace) -> int:
    config = oauth2imap.config.read()

    if isinstance(config, oauth2imap.Error):
        logger.critical("%s", config.message)
        return oauth2imap.EX_FAILURE

    provider = oauth2.get_upstream_provider(config)
    if not provider:
        return oauth2imap.EX_FAILURE

    verifier = secrets.token_urlsafe(90)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())[:-1]

    params: Dict[str,str] = {
        "client_id"             : provider["client-id"],
        "scope"                 : provider["scope"],
        "login_hint"            : provider["username"],
        "redirect_uri"          : provider["redirect-uri"],
        "code_challenge"        : challenge.decode(),
        "code_challenge_method" : "S256",
        "response_type"         : "code",
    }

    if "tenant" in provider:
        params["tenant"] = provider["tenant"]

    listen_port = 0

    if cmdargs.authflow == "localhostauthcode":
        listen_port = get_available_port()
        params["redirect_uri"] = f"http://localhost:{listen_port}/"

    print("URL:", provider["authorize-endpoint"] + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote))

    if cmdargs.authflow == "localhostauthcode":
        print("Visit displayed URL to authorize this application. Waiting...")
        authcode = get_localhost_authcode(listen_port)
    else:
        authcode = input("Visit displayed URL to retrieve authorization code. Enter "
                         "code from server (might be in browser address bar): ")

    if not authcode:
        logger.critical("Did not obtain an authcode")
        return oauth2imap.EX_FAILURE

    for key in "response_type", "login_hint", "code_challenge", "code_challenge_method":
        del params[key]

    params["grant_type"]    = "authorization_code"
    params["client_secret"] = provider["client-secret"]
    params["code"]          = authcode
    params["code_verifier"] = verifier

    logger.debug("Exchanging the authorization code for an access token")

    token = oauth2.get_token(provider, params)

    if not token:
        logger.critical("unable to get token")
        return oauth2imap.EX_FAILURE

    cache = oauth2.get_token_cache(config["upstream"]["tokens-file"])
    token_key = oauth2.get_token_key(provider)

    cache[token_key] = token

    oauth2.write_token_cache(config["upstream"]["tokens-file"], cache)

    return oauth2imap.EX_SUCCESS
