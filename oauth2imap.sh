#!/usr/bin/env bash
#
# Run oauth2imap from a git checkout.
#

REAL_SCRIPT=$(realpath -e ${BASH_SOURCE[0]})
SCRIPT_TOP="${SCRIPT_TOP:-$(dirname ${REAL_SCRIPT})}"

exec env PYTHONPATH="${SCRIPT_TOP}" python3 "${SCRIPT_TOP}/oauth2imap/command.py" "${@}"
