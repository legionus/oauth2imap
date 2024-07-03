#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import os.path
import pprint

from typing import Dict, Any

import msal # type: ignore

import oauth2imap

logger = oauth2imap.logger
cache = None

def __get_token_cache(filename: str) -> Any:
    global cache

    if not cache:
        cache = msal.SerializableTokenCache()

        if os.path.exists(filename):
            with open(filename, encoding="utf-8") as file:
                cache.deserialize(file.read())

    return cache


def __write_token_cache(filename: str) -> None:
    if cache and cache.has_state_changed:
        # TODO: flock needed.
        with open(filename, "w", encoding="utf-8") as file:
            file.write(cache.serialize())

    return None


def get_access_token(config: Dict[str,Any]) -> str | None:
    app = msal.PublicClientApplication(
            config["upstream"]["client-id"],
            authority=config["upstream"]["authority"],
            token_cache=__get_token_cache(config["upstream"]["tokens-file"]))

    result = None

    for account in app.get_accounts(username=config["upstream"]["username"]):
        logger.debug("Trying to refresh access token...")
        result = app.acquire_token_silent(scopes=config["upstream"]["scope"],
                                          account=account)
        break

    if not result or "access_token" not in result:
        logger.debug("Access token not found.")
        result = app.acquire_token_interactive(scopes=config["upstream"]["scope"],
                                               login_hint=config["upstream"]["username"])

    if not result or "access_token" not in result:
        logger.error(result.get("error"))
        logger.error(result.get("error_description"))
        logger.error(result.get("correlation_id"))
        return None

    __write_token_cache(config["upstream"]["tokens-file"])

    logger.debug(pprint.pformat(result))
    return str(result["access_token"])
