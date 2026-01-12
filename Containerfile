FROM docker.io/nvidia/cuda:12.9.1-base-ubuntu24.04

# Maybe we want mirror for package
ARG APT_ARCHIVES=http://archive.ubuntu.com
ARG APT_SECURITY=http://security.ubuntu.com
ARG GH_ENDPOINT=https://github.com
ARG PIP_INDEX=https://pypi.org

# Some tools version
ARG GOSU_TAG=1.19

# Models location
ENV MINERU_MODEL_SOURCE=local
ENV MINERU_MODEL_PIPELINE=/app/models/opendatalab--PDF-Extract-Kit-1.0
ENV MINERU_MODEL_VLM=/app/models/opendatalab--MinerU2.5-2509-1.2B

# Install required packages
RUN set -eux; \
    \
    if [ "${APT_ARCHIVES}" != "http://archive.ubuntu.com" ]; then \
        sed -i "s@http://archive.ubuntu.com@${APT_ARCHIVES}@g" /etc/apt/sources.list; \
    fi; \
    \
    export DEBIAN_FRONTEND=noninteractive; \
    apt update -y; \
    apt install \
        libgl1 libglib2.0-0 \
        python3 python3-venv \
        curl gettext-base gpg tree jq \
        -y; \
    apt clean && rm -rf /var/lib/apt/lists/*; \
    \
    if [ "${APT_ARCHIVES}" != "http://archive.ubuntu.com" ]; then \
        sed -i "s@${APT_ARCHIVES}@http://archive.ubuntu.com@g" /etc/apt/sources.list; \
    fi;

# Install gosu from release
RUN set -eux; \
    \
    cd /tmp; \
    \
    TARGET_ARCH=$(dpkg --print-architecture); \
    curl --progress-bar --location --output gosu $GH_ENDPOINT/tianon/gosu/releases/download/${GOSU_TAG}/gosu-${TARGET_ARCH}; \
    curl --progress-bar --location --output gosu.asc $GH_ENDPOINT/tianon/gosu/releases/download/${GOSU_TAG}/gosu-${TARGET_ARCH}.asc; \
    export GNUPGHOME="$(mktemp -d)"; \
    gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4; \
    gpg --batch --verify gosu.asc gosu; \
    gpgconf --kill all; \
    cp gosu /usr/local/bin/; \
    chmod +x /usr/local/bin/gosu; \
    \
    rm -rf /tmp/*;

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
COPY --chown=mineru:mineru . /app/

# Install dependencies packages
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
    \
    trusted_host="--trusted-host $(echo $PIP_INDEX | awk -F[/:] '{print $4}')"; \
    if [ "${PIP_INDEX#http://}" == "$PIP_INDEX" ]; then \
        trusted_host=""; \
    fi; \
    if [ -z "$PIP_INDEX" ]; then \
        echo "$PIP_INDEX should not be empty, aborted"; \
        exit 3; \
    fi; \
    \
    pip3 install \
        --requirement requirements.txt \
        --prefer-binary \
        --no-cache-dir \
        --no-color \
        --disable-pip-version-check \
        $trusted_host; \
    \
    rm -rf ~/.cache; \
    rm -rf ~/.config;

WORKDIR /app

VOLUME [ "/app/instance", "/app/models" ]

EXPOSE 9471/tcp

ENTRYPOINT [ "/app/entrypoint.sh" ]

CMD [ "prompt" ]
