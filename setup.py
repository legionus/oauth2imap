#!/usr/bin/env python3

import os
import re
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def find_version(source):
    version_file = read(source)
    version_match = re.search(r"^__VERSION__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


NAME = "oauth2imap"

setup(
        version=find_version("oauth2imap/__init__.py"),
        url="https://github.com/legionus/oauth2imap.git",
        name=NAME,
        description="imap server proxying access to another imap server with oauth2 authentication.",
        author="Alexey Gladkov",
        author_email="legion@kernel.org",
        packages=["oauth2imap"],
        license="GPLv3+",
        keywords=["imap", "server", "oauth2"],
        install_requires=[
            "msal>=1.29.0",
            ],
        python_requires=">=3.11",
        entry_points={
            "console_scripts": [
                "oauth2imap=oauth2imap.command:cmd"
                ],
            },
        )
