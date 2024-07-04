#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import os.path
import json
import hashlib
import urllib.parse
import urllib.request
import string
import pprint

from datetime import timedelta, datetime
from typing import Dict, Any

import oauth2imap

logger = oauth2imap.logger


class Token(Dict[str,str]):
    pass

class Provider(Dict[str,str]):
    pass

cache: Dict[str,Token] = {}
providers: Dict[str,Provider] = {}


def __register_google() -> None:
    providers["google"] = Provider({})
    providers["google"]["sasl-method"]         = "OAUTHBEARER"
    providers["google"]["imap-endpoint"]       = "imap.gmail.com"
    providers["google"]["client-id"]           = ""
    providers["google"]["client-secret"]       = ""
    providers["google"]["username"]            = ""
    providers["google"]["scope"]               = "https://mail.google.com/"
    providers["google"]["authority"]           = "https://accounts.google.com/o/oauth2"
    providers["google"]["authorize-endpoint"]  = "${authority}/auth"
    providers["google"]["token-endpoint"]      = "${authority}/token"
    providers["google"]["redirect-uri"]        = "urn:ietf:wg:oauth:2.0:oob"

def __register_microsoft() -> None:
    providers["microsoft"] = Provider({})
    providers["microsoft"]["sasl-method"]        = "XOAUTH2"
    providers["microsoft"]["imap-endpoint"]      = "outlook.office365.com"
    providers["microsoft"]["client-id"]          = ""
    providers["microsoft"]["client-secret"]      = ""
    providers["microsoft"]["username"]           = ""
    providers["microsoft"]["tenant"]             = "common"
    providers["microsoft"]["scope"]              = "https://outlook.office365.com/.default offline_access"
    providers["microsoft"]["authority"]          = "https://login.microsoftonline.com/${tenant}"
    providers["microsoft"]["authorize-endpoint"] = "${authority}/oauth2/v2.0/authorize"
    providers["microsoft"]["token-endpoint"]     = "${authority}/oauth2/v2.0/token"
    providers["microsoft"]["redirect-uri"]       = "https://login.microsoftonline.com/common/oauth2/nativeclient"

__register_google()
__register_microsoft()


def get_provider(name: str) -> Provider | None:
    return providers.get(name, None)


def get_upstream_provider(config: Dict[str,Any]) -> Provider | None:
    if "provider" not in config["upstream"]:
        logger.critical("provider required")
        return None

    if config["upstream"]["provider"] not in providers:
        logger.critical("unknown provider '%s'", config["upstream"]["provider"])
        return None

    provider = get_provider(config["upstream"]["provider"])
    if not provider:
        return None

    new = Provider({})

    for key in provider.keys():
        if key in config["upstream"]:
            new[key] = str(config["upstream"][key])
        else:
            new[key] = provider[key]

    for key in provider.keys():
        s = string.Template(new[key]).safe_substitute(new)
        new[key] = s

    return new


def get_token_cache(filename: str) -> Dict[str,Token]:
    global cache

    if not cache and os.path.exists(filename):
        with open(filename, encoding="utf-8") as file:
            data = file.read() or "{}"
            cache = json.loads(data)

    return cache


def write_token_cache(filename: str, new_cache: Dict[str,Token]) -> None:
    if cache:
        # TODO: flock needed.
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(new_cache, file, indent=4, sort_keys=True)

    return None


def valid_token(token: Token) -> bool:
    if "access_token_expiration" in token:
        token_exp = token["access_token_expiration"]
        if token_exp:
            return datetime.now() < datetime.fromisoformat(token_exp)
    return False


def get_token_key(provider: Provider) -> str:
    data = []
    for key in ("authorize-endpoint", "tenant", "client-secret", "client-id", "username"):
        if key in provider:
            data.append(provider[key])

    return hashlib.sha256(" ".join(data).encode()).hexdigest()


def get_token(provider: Provider, params: Dict[str,str]) -> Token | None:
    try:
        #
        # From: https://datatracker.ietf.org/doc/html/rfc6749#section-4.1.3
        #
        # The client makes a request to the token endpoint by sending the
        # following parameters using the "application/x-www-form-urlencoded"
        # format.
        #
        req = urllib.request.Request(
                method="POST",
                url=provider["token-endpoint"],
                data=urllib.parse.urlencode(params).encode(),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
        )
        response = urllib.request.urlopen(req)

    except urllib.error.HTTPError as err:
        logger.debug("http error: code=%s reason=%s", err.code, err.reason)
        response = err

    response = response.read()
    result = json.loads(response)

    logger.debug(pprint.pformat(result))

    if "access_token" in result:
        d = {
            "access_token": result["access_token"],
            "access_token_expiration": (datetime.now() + timedelta(seconds=int(result["expires_in"]))).isoformat(),
            "refresh_token": "",
        }
        if "refresh_token" in result:
            d["refresh_token"] = result["refresh_token"]

        return Token(d)

    if "error_description" in result:
        logger.critical("unable refresh token: %s", result["error_description"])
        return None

    if "error" in result:
        logger.critical("unable refresh token: %s", result["error"])
        return None

    logger.critical("unable refresh token")
    return None


def do_refresh_token(provider: Provider, token: Token) -> Token | None:
    if "refresh_token" not in token or not token["refresh_token"]:
        logger.critical("no refresh token")
        return None

    logger.debug("refreshing token ...")

    params = {
        "client_id": provider["client-id"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }

    if "tenant" in provider:
        params["tenant"] = provider["tenant"]

    return get_token(provider, params)


def get_access_token(config: Dict[str,Any]) -> str | None:
    cache = get_token_cache(config["upstream"]["tokens-file"])

    provider = get_upstream_provider(config)
    if not provider:
        return None

    token_key = get_token_key(provider)
    token = None

    if token_key in cache:
        token = cache[token_key]

        if not valid_token(token):
            token = do_refresh_token(provider, token)

    if not token:
        logger.critical("no valid access token")
        return None

    if not valid_token(token):
        logger.critical("unable to get actual access token")
        return None

    return str(token["access_token"])


def sasl_string(provider: Provider, token: str) -> bytes | None:
    user = provider["username"]
    host = provider["imap-endpoint"]
    port = 993

    if provider["sasl-method"] == "OAUTHBEARER":
        return f"n,a={user},\x01host={host}\x01port={port}\x01auth=Bearer {token}\x01\x01".encode()

    if provider["sasl-method"] == "XOAUTH2":
        return f"user={user}\x01auth=Bearer {token}\x01\x01".encode()

    return None
