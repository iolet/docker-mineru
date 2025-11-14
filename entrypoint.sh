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
if [ ! -L "${nv_prefix}/cudnn/lib/libcudnn.so" ]; then
    cd "${nv_prefix}/cudnn/lib"; \
    ln -s libcudnn.so.9 libcudnn.so; \
fi
if [ ! -L "${nv_prefix}/cublas/lib/libcublas.so" ]; then
    cd "${nv_prefix}/cublas/lib"; \
    ln -s libcublas.so.12 libcublas.so;
fi
cd $workdir

export LD_LIBRARY_PATH=${nv_prefix}/cudnn/lib:${nv_prefix}/cublas/lib

# Ensure target correct
if [ "prompt" = "${1}" ]; then
    echo "missing argument <app>, available:"
    echo "    api    for sync api endpoint serve"
    echo "    queue  for async background task"
    exit 1
elif [ "api" = "${1}" ]; then
    set -- /app/.venv/bin/gunicorn --config gunicorn.conf.py
elif [ "queue" = "${1}" ]; then
    set -- /app/.venv/bin/celery \
        --app src.mineru_pdf.celery.app \
        worker \
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

# Migrate database and link directory
. .venv/bin/activate
flask db upgrade
if [ ! -L "/app/instance/public/archives" ]; then
    flask storage link
fi
deactivate

# Fix permission and Clean variables
chown --recursive mineru:mineru "${prefix}"
unset prefix subdirs subdir nv_prefix workdir

exec gosu mineru "$@"
