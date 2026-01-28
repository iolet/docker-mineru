#!/usr/bin/awk -f

BEGIN {
    FS = "[ :]"
}

/^FROM\s*/ {
    line=$2
}

END {
    print line
}
