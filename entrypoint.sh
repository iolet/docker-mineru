#!/usr/bin/sh

# Ensure instance folders exists
prefix="/app/instance"
for item in "archives cache logs public"; do
    if [ ! -d "${prefix}/${item}" ]; then
        mkdir -p "${prefix}/${item}"
    fi
done

exec gosu mineru "$@"
