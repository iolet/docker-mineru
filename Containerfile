# Defined a base nvidia/cuda image
ARG CUDA_TAG=12.8.1-base-ubuntu24.04

# We need get verified binary
FROM docker.io/nvidia/cuda:${CUDA_TAG} AS builder

# Maybe we want mirror for package
ARG APT_ARCHIVES=http://archive.ubuntu.com
ARG APT_SECURITY=http://security.ubuntu.com
ARG GH_ENDPOINT=https://github.com

# Some tools version
ARG GOSU_TAG=1.19

# Install required packages
RUN set -eux; \
    \
    if [ "${APT_ARCHIVES}" != "http://archive.ubuntu.com" ]; then \
        sed -i "s@http://archive.ubuntu.com@${APT_ARCHIVES}@g" /etc/apt/sources.list; \
    fi; \
    \
    export DEBIAN_FRONTEND=noninteractive; \
    apt update -y; \
    apt install curl gpg -y; \
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
    find /tmp -type d -path '/tmp/**' -print0 | xargs -0 rm -rf;

# Ensure argument is available in next stage
ARG CUDA_TAG

# Start build a fresh image
FROM docker.io/nvidia/cuda:${CUDA_TAG}

# Maybe we want mirror for package (referenced)
ARG APT_ARCHIVES
ARG APT_SECURITY
ARG PIP_INDEX=https://pypi.org

# Models location
ENV MINERU_MODEL_SOURCE=local
ENV MINERU_MODEL_PIPELINE=/app/models/opendatalab--PDF-Extract-Kit-1.0
ENV MINERU_MODEL_VLM=/app/models/opendatalab--MinerU2.5-2509-1.2B

# Copy verified gosu binary
COPY --from=builder /usr/local/bin/gosu /usr/local/bin/gosu

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
        cuda-nvcc-12-8 \
        gettext-base \
        libgl1 libglib2.0-0 \
        ninja-build \
        python3 python3-dev python3-venv \
        -y; \
    apt clean && rm -rf /var/lib/apt/lists/*; \
    \
    if [ "${APT_ARCHIVES}" != "http://archive.ubuntu.com" ]; then \
        sed -i "s@${APT_ARCHIVES}@http://archive.ubuntu.com@g" /etc/apt/sources.list; \
    fi;

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

# Install dependencies packages and apply patches
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
    py_ver=$(find .venv/lib -type d -name 'python3\.??' | tail -n 1 | xargs basename | sed 's/\./\\\./'); \
    for pfile in $(ls -1 -S patches/*.patch); do \
        sed "s/python3\.[0-9]\+/$py_ver/g" "$pfile" | patch --strip 1 --unified; \
    done; \
    unset py_ver; \
    \
    rm -rf ~/.cache; \
    rm -rf ~/.config; \
    find /tmp -type d -path '/tmp/**' -print0 | xargs -0 rm -rf;

# Setup workdir
WORKDIR /app

# Persist directories
VOLUME [ "/app/instance", "/app/models" ]

# Expose port for wsgi and vllm
EXPOSE 9471/tcp
EXPOSE 30000/tcp

ENTRYPOINT [ "/app/entrypoint.sh" ]

CMD [ "prompt" ]
