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
if [ ! -f "/app/mineru.json" ]; then
    envsubst < mineru.json.template > mineru.json
fi

# Ensure nvidia headers and libraries available
nv_prefix=/app/.venv/lib/python3.12/site-packages/nvidia
if [ -d "$nv_prefix" ]; then
    headers=$(find $nv_prefix -type d -path "**/include" | tr '\n' ':' | sed 's/:$//')
    [ -z "$headers" ] || export CPATH="$headers"
    unset headers
    libraries=$(find $nv_prefix -type d -path "**/lib" | tr '\n' ':' | sed 's/:$//')
    [ -z "$libraries" ] || export LD_LIBRARY_PATH="$libraries"
    unset libraries
fi

# Workaround for cudnn and cublas not found
workdir=$(pwd)
if [ -d "${nv_prefix}/cudnn/lib" ] && [ ! -L "${nv_prefix}/cudnn/lib/libcudnn.so" ]; then
    cd "${nv_prefix}/cudnn/lib"; \
    ln -s libcudnn.so.9 libcudnn.so; \
fi
if [ -d "${nv_prefix}/cublas/lib" ] && [ ! -L "${nv_prefix}/cublas/lib/libcublas.so" ]; then
    cd "${nv_prefix}/cublas/lib"; \
    ln -s libcublas.so.12 libcublas.so;
fi
cd $workdir

# Redirect config and cache to volume by default
if [ -z "$XDG_CONFIG_HOME" ]; then
    export XDG_CONFIG_HOME=/app/instance/config
fi
if [ -z "$XDG_CACHE_HOME" ]; then
    export XDG_CACHE_HOME=/app/instance/cache
fi

# Ensure target correct
if [ "prompt" = "${1}" ]; then
    echo "missing argument <app>, available:"
    echo "    serve  for api endpoint serve"
    echo "    queue  for background task"
    echo "    vllm   for model serve"
    exit 1
elif [ "serve" = "${1}" ]; then
    set -- /app/.venv/bin/gunicorn --config gunicorn.conf.py
elif [ "queue" = "${1}" ]; then
    # todo get soft-time-limit from time-limit
    set -- /app/.venv/bin/celery \
        --app src.mineru_pdf.celery.app \
        worker \
        --concurrency ${QUEUE_CONCURRENCY:-"1"} \
        --time-limit ${QUEUE_TIMEOUT:-"1800"} \
        --soft-time-limit ${QUEUE_TIMEOUT_THRESHOLD:-"1500"} \
        --optimization fair \
        --prefetch-multiplier 1 \
        --max-tasks-per-child 10 \
        --loglevel ${LOGLEVEL:-"INFO"}
elif [ "schedule" = "${1}" ]; then
    set -- /app/.venv/bin/celery \
        --app src.mineru_pdf.celery.app \
        beat \
        --schedule /app/instance/beat-stat.db \
        --loglevel ${LOGLEVEL:-"INFO"}
elif [ "vllm" = "${1}" ]; then
    set -- /app/.venv/bin/mineru-vllm-server \
        --port ${VLLM_PORT:-"30000"} \
        --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION:-"0.5"}
else
    exec "$@"
fi

# Ensure models path exists
if [ ! -d "${MINERU_MODEL_PIPELINE}" ]; then
    echo "MINERU_MODEL_PIPELINE (${MINERU_MODEL_PIPELINE}) not exists"
    exit 3
fi
if [ ! -d "${MINERU_MODEL_VLM}" ]; then
    echo "MINERU_MODEL_VLM (${MINERU_MODEL_VLM}) not exists"
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
