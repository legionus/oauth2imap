#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import os.path
import tomllib

from typing import Dict, Any

import oauth2imap

logger = oauth2imap.logger


def read() -> Dict[str, Any] | oauth2imap.Error:
    config = None

    config_file = os.path.expanduser("~/.oauth2imaprc")

    if os.path.exists(config_file):
        logger.debug("picking config file `%s' ...", config_file)

        with open(config_file, "rb") as f:
            config = tomllib.load(f)

    if not config:
        return oauth2imap.Error("config file not found")

    logger.info("config has been read")
    return config
