FROM docker.io/nvidia/cuda:12.4.1-base-ubuntu22.04

ARG APT_ARCHIVES=http://archive.ubuntu.com
ARG APT_SECURITY=http://security.ubuntu.com
ARG PIP_INDEX=https://pypi.org
ARG PIP_EXTRA=https://pypi.example.com

ENV MODEL_PDFEXTRACTKIT_PATH=/app/models/opendatalab--PDF-Extract-Kit-1.0
ENV MODEL_LAYOUTREADER_PATH=/app/models/ppaanngggg--layoutreader

# Install required packages
RUN set -eux; \
    \
    if [ "${APT_ARCHIVES}" != "http://archive.ubuntu.com" ]; then \
        sed -i "s@http://archive.ubuntu.com@${APT_ARCHIVES}@g" /etc/apt/sources.list; \
    fi; \
    \
    export DEBIAN_FRONTEND=noninteractive; \
    \
    apt update -y; \
    apt install \
        python3 python3-venv \
        curl gettext-base tree jq \
        -y; \
    apt clean && rm -rf /var/lib/apt/lists/*; \
    \
    if [ "${APT_ARCHIVES}" != "http://archive.ubuntu.com" ]; then \
        sed -i "s@${APT_ARCHIVES}@http://archive.ubuntu.com@g" /etc/apt/sources.list; \
    fi;

# Install gosu for dropping root user
RUN set -eux; \
    \
    cd \tmp; \
    \
    curl --progress-bar --location --remote-name https://github.com/tianon/gosu/releases/download/1.19/gosu-amd64; \
    curl --progress-bar --location --remote-name https://github.com/tianon/gosu/releases/download/1.19/SHA256SUMS; \
    sha256sum --check --strict --ignore-missing SHA256SUMS; \
    cp gosu-amd64 /usr/local/bin/gosu; \
    chmod +x /usr/local/bin/gosu; \
    \
    rm -rf \tmp\*;

# Added rootless user and group
RUN set -eux; \
    adduser \
        --system \
        --home /app \
        --shell /usr/sbin/nologin \
        --gecos mineru \
        --group \
        --disabled-password \
        mineru;

# Copy project files
COPY src /app/
COPY .env.example .flaskenv gunicorn.conf.py requirements.txt /app/

# Install dependent packages
RUN set -eux; \
    \
    export PYTHONUNBUFFERED=1; \
    cd /app; \
    \
    python3 -m venv .venv; \
    . .venv/bin/activate; \
    \
    if [ "${PIP_INDEX}" != "https://pypi.org" ]; then \
        pip config set global.index-url $PIP_INDEX; \
    fi; \
    if [ "${PIP_EXTRA}" != "https://pypi.example.com" ]; then \
        pip config set global.extra-index-url $PIP_EXTRA; \
    fi; \
    \
    pip3 install \
        "wheel~=0.45.1" \
        --no-cache-dir \
        --no-color \
        --disable-pip-version-check; \
    pip3 install \
        --requirement requirements.txt \
        --no-cache-dir \
        --no-color \
        --disable-pip-version-check; \
    \
    rm -rf ~/.cache; \
    rm -rf ~/.config;

# Added entrypoint.sh
COPY entrypoint.sh /usr/local/bin/

WORKDIR /app

VOLUME [ "/app/.cache", "/app/instance", "/app/models" ]

EXPOSE 8080/tcp

ENTRYPOINT [ "entrypoint.sh" ]

CMD [ "api" ]
