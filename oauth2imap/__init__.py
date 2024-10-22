# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

import os.path
import logging

__VERSION__ = '1'

EX_SUCCESS = 0 # Successful exit status.
EX_FAILURE = 1 # Failing exit status.

logger = logging.getLogger("oauth2imap")

class Error:
    def __init__(self, message: str):
        self.message = message


def setup_logger(logger: logging.Logger, level: int, fmt: str,
                 logfile: str | None) -> logging.Logger:
    formatter = logging.Formatter(fmt=fmt)

    handler: logging.Handler

    if logfile:
        logfile = os.path.expanduser(logfile)
        handler = logging.FileHandler(logfile, mode='a', encoding="utf-8")
    else:
        handler = logging.StreamHandler()

    handler.setLevel(level)
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
