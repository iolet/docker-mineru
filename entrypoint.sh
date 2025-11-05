#!/usr/bin/sh

# Ensure instance folders exists
prefix="/app/instance"
subdirs="archives cache logs public"
for subdir in $subdirs; do
    if [ ! -d "${prefix}/${subdir}" ]; then
        mkdir -p "${prefix}/${subdir}"
    fi
done

# Generate magic pdf config file
if [ ! -f "/app/magic-pdf.json" ]; then
    envsubst < magic-pdf.json.template > magic-pdf.json
fi

# Workaround for cudnn and cublas not found
nv_prefix=/app/.venv/lib/python3.10/site-packages/nvidia

workdir=$(pwd)
cd "${nv_prefix}/cudnn/lib"; \
ln -s libcudnn.so.9 libcudnn.so; \
cd "${nv_prefix}/cublas/lib"; \
ln -s libcublas.so.12 libcublas.so;
cd $workdir

export LD_LIBRARY_PATH=${nv_prefix}/cudnn/lib:${nv_prefix}/cublas/lib

# Ensure target correct
if [ "api" = "${1}" ]; then
    set -- /app/.venv/bin/gunicorn --config gunicorn.conf.py
elif [ "queue" = "${1}" ]; then
    set -- /app/.venv/bin/celery worker \
        --app src.mineru_pdf.celery.app \
        --concurrency 1 \
        --time-limit 1800 \
        --soft-time-limit 1500 \
        --optimization fair \
        --prefetch-multiplier 1 \
        --max-tasks-per-child 10 \
        --loglevel DEBUG
else
    exec "$@"
fi

# Ensure models path exists
if [ ! -d "${MODEL_PDFEXTRACTKIT_PATH}" ]; then
    echo "MODEL_PDFEXTRACTKIT_PATH (${MODEL_PDFEXTRACTKIT_PATH}) not exists"
    exit 3
fi
if [ ! -d "${MODEL_LAYOUTREADER_PATH}" ]; then
    echo "MODEL_LAYOUTREADER_PATH (${MODEL_LAYOUTREADER_PATH}) not exists"
    exit 3
fi

# Migrate database
. .venv/bin/activate
flask db upgrade
deactivate

# Fix permission and Clean variables
chown --recursive mineru:mineru "${prefix}"
unset prefix

exec gosu mineru "$@"
