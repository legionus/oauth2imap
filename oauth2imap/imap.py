#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import imaplib

from typing import Dict, Tuple, List, Any

import oauth2imap
import oauth2imap.config
import oauth2imap.auth as auth
import oauth2imap.oauth2 as oauth2

CRLF = '\r\n'

logger = oauth2imap.logger


def parse_client_command(line: str) -> Tuple[str,str,str]:
    #
    # From: https://datatracker.ietf.org/doc/html/rfc9051#section-2.2.1
    #
    # The client command begins an operation. Each client command is
    # prefixed with an identifier (typically a short alphanumeric
    # string, e.g., A0001, A0002, etc.) called a "tag". A different
    # tag is generated by the client for each command.
    #
    tag, args = line.split(" ", 1)
    args = args.strip()

    cmd = ""
    if " " in args:
        cmd, args = args.split(" ", 1)
        cmd = cmd.upper()
    else:
        cmd = args.upper()
        args = ""

    return tag, cmd, args


def parse_server_command(line: str) -> Tuple[str,str]:
    #
    # From: https://datatracker.ietf.org/doc/html/rfc9051#section-7.1
    #
    # Generic Status Responses are OK, NO, BAD, PREAUTH, and BYE. OK, NO, and
    # BAD can be tagged or untagged. PREAUTH and BYE are always untagged.
    #
    s = line.split(" ")

    if len(s) > 1:
        # Untagged.
        if s[0] == "*" and s[1] in ('OK', 'NO', 'BAD', 'PREAUTH', 'BYE'):
            return "*", s[1]

        # Server asks for more.
        if s[0] == "+":
            return "+", ""

        # Tagged.
        if s[1] in ('OK', 'NO', 'BAD'):
            return s[0], s[1]

    # Something unknown.
    return "", ""


class Context(Dict[str, Any]):
    pass


class Downstream:
    def __init__(self, addr: str, rfile: Any, wfile: Any):
        self.addr  = addr
        self.rfile = rfile
        self.wfile = wfile

    def readable(self) -> bool:
        return not self.rfile.closed and self.rfile.readable()

    def recv_bytes(self) -> Any:
        line = self.rfile.readline()
        logger.debug("--> downstream: %s: %s", self.addr, line)
        return line

    def send_bytes(self, msg: bytes) -> None:
        logger.debug("<-- downstream: %s: %s", self.addr, msg)
        self.wfile.write(msg)
        self.wfile.flush()

    def recv(self) -> Any:
        return self.recv_bytes().decode()

    def send(self, ans: List[str]) -> None:
        msg = " ".join(ans) + CRLF
        self.send_bytes(msg.encode())

    def command_capability(self, ctx: Context, up_caps: Tuple[str, ...]) -> None:
        caps = ["*", "CAPABILITY", "IMAP4rev1"]

        if "username" in ctx and "password" in ctx:
            caps.extend(["AUTH=CRAM-MD5", "AUTH=PLAIN"])

        for cap in up_caps:
            if not cap.startswith("AUTH="):
                caps.append(cap)

        self.send(caps)
        self.send([ctx["tag"], "OK", "CAPABILITY completed"])

    def command_authenticate(self, ctx: Context, arg: str) -> bool:
        if arg not in ("CRAM-MD5"):
            self.send([ctx["tag"], "NO", "unsupported authentication mechanism"])
            return False

        def auth_interact(shared: str) -> Any:
            self.send(["+", shared])
            return self.recv()

        (ret, msg) = auth.cram_md5(ctx["username"], ctx["password"], auth_interact)
        if not ret:
            self.send([ctx["tag"], "NO", msg])
            return False

        self.send([ctx["tag"], "OK", "CRAM-MD5 authentication successful"])
        return True

    def command_login(self, ctx: Context, args: str) -> bool:
        (ret, msg) = auth.plain(ctx["username"], ctx["password"], args)
        if not ret:
            self.send([ctx["tag"], "NO", msg])
            return False

        self.send([ctx["tag"], "OK", "LOGIN authentication successful"])
        return True


class Upstream:
    def __init__(self, addr: str, port: int):
        self.addr = (addr, port)
        self.imap = imaplib.IMAP4_SSL(self.addr[0], self.addr[1])
        self.imap.debug = 4

    def authenticate(self, config: Dict[str,Any]) -> bool:
        logger.debug("Auth ...")

        token = oauth2.get_access_token(config)
        if not token:
            logger.critical("%s: unable to get access token", self.addr)
            return False

        username = config["upstream"]['username']
        password = token

        def auth_string(_: Any) -> bytes | None:
            s = f"user={username}\x01auth=Bearer {password}\x01\x01"
            return s.encode()

        try:
            typ, dat = self.imap.authenticate("XOAUTH2", auth_string)
            if typ == "OK":
                return True
            logger.critical("%s: %s", self.addr, dat)
        except Exception:
            pass

        return False

    def recv_bytes(self) -> Any:
        line = self.imap.readline()
        logger.debug("-->   upstream: %s: %s", self.addr, line)
        return line

    def send_bytes(self, msg: bytes) -> None:
        logger.debug("<--   upstream: %s: %s", self.addr, msg)
        self.imap.send(msg)


def session(config: Dict[str,Any], ds: Downstream, up: Upstream) -> bool:
    ctx = Context({})

    for param in ("username", "password"):
        if param in config["downstream"]:
            ctx[param] = config["downstream"][param]

    session = True
    authorized = False

    try:
        if not up.authenticate(config):
            return False

        ds.send(["*", "OK", "IMAP4rev1 Service Ready"])

        #
        # From: https://datatracker.ietf.org/doc/html/rfc9051#section-2.2
        #
        # All interactions transmitted by client and server are in the form
        # of lines, that is, strings that end with a CRLF. The protocol
        # receiver of an IMAP4rev2 client or server is reading either a line
        # or a sequence of octets with a known count followed by a line.
        #
        while session:
            if not ds.readable():
                break

            line = ds.recv_bytes()
            if line.rstrip(CRLF.encode()) == b"":
                continue

            #
            # From: https://datatracker.ietf.org/doc/html/rfc9051#section-2.2.1
            #
            # The client command begins an operation. Each client command is
            # prefixed with an identifier (typically a short alphanumeric
            # string, e.g., A0001, A0002, etc.) called a "tag". A different
            # tag is generated by the client for each command.
            #
            # There are two cases in which a line from the client does not
            # represent a complete command. In one case, a command argument
            # is quoted with an octet count; in the other case, the command
            # arguments require server feedback (see the AUTHENTICATE
            # command). In either case, the server sends a command
            # continuation request response if it is ready for the octets
            # (if appropriate) and the remainder of the command. This
            # response is prefixed with the token "+".
            #
            tag, cmd, args = parse_client_command(line.decode().rstrip(CRLF))
            ctx["tag"] = tag

            if cmd == "LOGOUT":
                session = False

            if not authorized:
                if cmd == "CAPABILITY":
                    ds.command_capability(ctx, up.imap.capabilities)
                    continue
                if cmd == "AUTHENTICATE":
                    authorized = ds.command_authenticate(ctx, args)
                    continue
                if cmd == "LOGIN":
                    authorized = ds.command_login(ctx, args)
                    continue

            up.send_bytes(line)

            #
            # From: https://datatracker.ietf.org/doc/html/rfc9051#section-7
            #
            # Server responses are in three forms: status responses, server
            # data, and command continuation requests.
            #
            # The client MUST be prepared to accept any response at all
            # times.
            #
            while True:
                line = up.recv_bytes()
                ds.send_bytes(line)

                tag, status = parse_server_command(line.decode().rstrip(CRLF))
                if status and tag == ctx["tag"]:
                    break

    except (BrokenPipeError, ConnectionResetError) as e:
        logger.debug("connection error: %s", e)

    except Exception as e:
        logger.critical("got exception: %s", e)
        return False

    return True
