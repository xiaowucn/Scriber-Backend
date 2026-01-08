FROM registry.cheftin.cn/p/scriber-runtime as builder

WORKDIR /opt/scriber

ARG env=env

ENV ENV=${env}

RUN --mount=type=bind,source=./,target=/builder cp -a /builder/. /opt/scriber && \
    apt update -y && \
    DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y \
        shc && \
    pip3 install pip uv --upgrade --no-cache-dir && \
    uv sync --no-group dev  && \
    python3 -m remarkable.config && \
    wget -q http://fm.paodingai.com/api/public/dl/cZ9CoSAs -O /tmp/AutoDoc.Crypto && \
    chmod 755 /tmp/AutoDoc.Crypto && \
    if [ -f ./bin/dr/conf/"config-${ENV}.yml" ]; then /tmp/AutoDoc.Crypto ./bin/dr/conf/"config-${ENV}.yml" || true; fi && \
    ./docker/cyc && \
    rm -rf ./docker/cyc config/*.yml ./bin/dr/conf/*.yml ./i18n/locales/Scriber-Backend.pot && \
    rm -rf /opt/scriber/data/files /opt/scriber/data/export_answer_data /opt/scriber/data/training_cache


FROM registry.cheftin.cn/p/scriber-runtime

WORKDIR /opt/scriber

ARG env=env

ENV ENV=${env} \
    LANG=en_US.UTF-8 \
    TZ=Asia/Shanghai \
    PYTHONPATH=/tmp/.local/lib/python3.12/site-packages/:/opt/scriber \
    SCRIBER_WORKER_NUM=4 \
    SCRIBER_WORKER_TRAINING_NUM=2


RUN --mount=type=bind,from=builder,source=/opt/scriber,target=/builder cp -a /builder/. /opt/scriber/ && \
    pip3 install pip uv --upgrade --no-cache-dir && \
    uv sync --no-group dev  && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
      pip3 install --index-url http://100.64.0.1:3141/cheftin/pypi --trusted-host 100.64.0.1 --target=/usr/lib/paoding/dist-packages/ psycopg2-gauss --upgrade --no-cache; \
    elif [ "$ARCH" = "aarch64" ]; then \
      pip3 download palladium==0.5.28+hs --index-url http://100.64.0.1:3141/cheftin/pypi --trusted-host 100.64.0.1 --no-deps -d /opt/pypi/ ; \
    fi && \
    rm -rf /etc/nginx/sites-enabled/default /opt/scriber/misc/prod-requirements.txt /tmp/* && \
    mkdir /data && \
    mv docker /docker && \
    chmod +x /docker/fix_permission.sh && \
    /docker/fix_permission.sh

ENTRYPOINT ["/docker/docker-entrypoint.sh"]
HEALTHCHECK --interval=30s --timeout=30s --retries=3 CMD ["python3", "/docker/healthcheck.pyc"]
