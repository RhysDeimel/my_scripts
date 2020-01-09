#!/usr/bin/env bash
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
NC=$'\033[0m' # No Color

# take first arg as path to check
files=$(find "$1" -type f -iname '*.yaml')

for file in $files; do
    printf "Checking %s: " "$file"
    error=$(aws cloudformation validate-template --template-body "file://$file" 2>&1)
    check=$?  # saving exit status to check helps prevent shenanigans

    # wasn't a success
    if [ ! "$check" -eq 0 ]; then
        printf "%sFAILED%s\n" "$RED" "$NC" 
        echo "$error"
        exit 1
    fi
    
    printf "%sPASS%s\n" "$GREEN" "$NC" 
done

# linted with shellcheck
# https://github.com/koalaman/shellcheck