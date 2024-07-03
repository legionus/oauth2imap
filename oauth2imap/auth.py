#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024  Alexey Gladkov <legion@kernel.org>

__author__ = 'Alexey Gladkov <legion@kernel.org>'

import base64
import binascii
import hashlib
import hmac
import os
import random
import time

from typing import Callable, Tuple

import oauth2imap

logger = oauth2imap.logger

def cram_md5(user: str, password: str, interact: Callable[[str], str]) -> Tuple[bool, str]:
    pid = os.getpid()
    now = time.time_ns()
    rnd = random.randrange(2**32 - 1)
    shared = f"<{pid}.{now}.{rnd}@oauth2imap>"

    line = interact(base64.b64encode(shared.encode()).decode())

    try:
        buf = base64.standard_b64decode(line).decode()
    except binascii.Error:
        return (False, "couldn't decode your credentials")

    fields = buf.split(" ")

    if len(fields) != 2:
        return (False, "wrong number of fields in the token")

    hexdigest = hmac.new(password.encode(),
                         shared.encode(),
                         hashlib.md5).hexdigest()

    if hmac.compare_digest(user, fields[0]) and hmac.compare_digest(hexdigest, fields[1]):
        return (True, "authentication successful")

    return (False, "authenticate failure")


def plain(user: str, password: str, arg: str) -> Tuple[bool, str]:
    known = [ user, password ]
    given = arg.split(" ", 1)
    valid = 0

    for i,_ in enumerate(known):
        k = hashlib.sha256(known[i].encode()).hexdigest()
        g = hashlib.sha256(given[i].encode()).hexdigest()

        if hmac.compare_digest(k, g):
            valid += 1

    if valid == len(known):
        return (True, "authentication successful")

    return (False, "authenticate failure")
