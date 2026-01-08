#!/bin/bash

set -x
export SKIP_SCHEMA_OVERWRITE=True

apt update || true
DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y build-essential gcc

# pip install libs
pip3 install pip --upgrade --no-cache-dir
uv sync --no-group dev

if [[ ${PSYCOPG2_GAUSS,,} == "true" ]]; then
  pip3 install --index-url http://100.64.0.1:3141/cheftin/pypi --trusted-host 100.64.0.1 --target=/usr/lib/paoding/dist-packages/ psycopg2-gauss --upgrade --no-cache
fi

rm -rf /docker
cp -r docker /docker
cp -r docker/*.py ./

chmod +x /docker/docker-entrypoint.sh
chmod +x /docker/patch_installer.sh

/docker/docker-entrypoint.sh "$@"
