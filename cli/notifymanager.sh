#!/usr/bin/env bash

export EVA_DIR=$(realpath "$(dirname "$(realpath "$0")")/..")
PYTHON="${EVA_DIR}"/venv/bin/python
export EVA_PRODUCT=`basename $0 | cut -d\- -f1`

cd "$EVA_DIR" || exit 1

"${PYTHON}" "${EVA_DIR}"/cli/notifymanager.py "$@"
