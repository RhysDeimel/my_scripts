#!/usr/bin/env bash

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
NC=$'\033[0m' # No Color

# checking for python virtualenv
if [ ! -d "/tmp/venv/" ]; then
    echo "Creating python3 virtualenv"
    python3 --version
    python3 -m ensure-pip
    python3 -m venv /tmp/venv || exit 1
fi

# check for cfn-lint
/tmp/venv/bin/python3 -m pip list | grep cfn-lint > /dev/null
check=$?  # saving exit status to check helps prevent shenanigans
if [ ! "$check" -eq 0 ]; then
    echo "Installing cfn-lint"
    /tmp/venv/bin/python3 -m pip install -q cfn-lint
fi

directories=$(find "$1" -type d)

for directory in $directories; do
	printf "Linting %s: " "$directory"
	error=$(/tmp/venv/bin/python3 -m cfnlint "$directory/*.yaml" 2>&1)
    check=$?

    if [ ! "$check" -eq 0 ]; then
        printf "%sFAILED%s\n" "$RED" "$NC" 
        echo "$error"
        exit 1
    fi
    
    printf "%sPASS%s\n" "$GREEN" "$NC" 
done

# linted with shellcheck
# https://github.com/koalaman/shellcheck