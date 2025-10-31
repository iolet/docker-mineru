#!/usr/bin/sh

# Ensure instance folders exists
prefix="/app/instance"
for item in "archives cache logs public"; do
    if [ ! -d "${prefix}/${item}" ]; then
        mkdir -p "${prefix}/${item}"
    fi
done

# Migrate database
. .venv/bin/activate
flask db upgrade
deactivate

# Clean variables
unset prefix

exec gosu mineru "$@"
