#!/bin/bash

set -e

# no root
if [[ "$(id -u)" == '0' ]] && [[ "${SKIP_NON_ROOT}" != "true" ]]; then
  if [[ -n "${HOST_USER_ID}" ]]; then
    USER_ID=${HOST_USER_ID:=1000}
    GROUP_ID=${HOST_GROUP_ID:=1000}
    if [[ $(id -u scriber 2>/dev/null) != "${USER_ID}" ]]; then
      userdel -r -f scriber || true
      groupadd -g "${GROUP_ID}" scriber
      useradd -r -m -u "${USER_ID}" -g "${GROUP_ID}" scriber
    fi
  fi
  find /data -maxdepth 1 -type d \! -user scriber -exec chown -R scriber.scriber '{}' +
  chown scriber /dev/fd/1 /dev/fd/2
  exec gosu scriber "/docker/docker-entrypoint.sh" "$@"
fi

# run worker
export SCRIBER_WEB_NUM=${SCRIBER_WEB_NUM:-2}
export SCRIBER_ASSOCIATION_NUM=${SCRIBER_ASSOCIATION_NUM:-2}
export SCRIBER_WORKER_NUM=${SCRIBER_WORKER_NUM:-4}
export SCRIBER_WORKER_TRAINING_NUM=${SCRIBER_WORKER_TRAINING_NUM:-2}

# nvidia runtime default
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/cuda/lib64:/usr/local/cuda/extras/CUPTI/lib64

# set user site-packages
export HOME=/tmp/
export PYTHONPATH=${PYTHONPATH}

if [ -d "/data/data/trainning_cache" ]; then
  mv /data/data/trainning_cache /data/data/training_cache
fi

WORK_DIR='/opt/scriber'
cd ${WORK_DIR}

rm -rf /data/tmp

mkdir -p /data/logs /data/patch /data/tmp
mkdir -p /data/data/files /data/data/export_answer_data /data/data/prompter /data/data/tbl_headers /data/data/training_cache

# k8s log
if [[ ! ("${ENABLE_STDOUT_LOG}" == "true" || (-n "${KUBERNETES_SERVICE_HOST}" && "${DISABLE_K8S_LOG}" != "true")) ]]; then
  exec 1>>/data/logs/init.log 2>&1
fi

install_patch() {
  if [[ -f "/docker/patch_installer.sh" ]]; then
    /docker/patch_installer.sh
  fi
  if [[ "${ENABLE_HS}" == "true" ]]; then
    pip3 install /opt/pypi/palladium-*hs-*.whl --force-reinstall --no-deps
  fi
}

if [[ ${PSYCOPG2_GAUSS,,} == "true" ]]; then
  export PYTHONPATH=/usr/lib/paoding/dist-packages/:${PYTHONPATH}
fi

# patch
install_patch

if [[ "${NVIDIA_VISIBLE_DEVICES}" == "" ]]; then
  export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/cuda/targets/x86_64-linux/lib/stubs
fi

read_config_with_jq() {
  RESULT=$(python3 -c "import json; from remarkable.config import get_config; print(json.dumps(get_config('')))" 2>/dev/null | jq "$@" 2>/dev/null)
  echo "${RESULT}"
}

# init
rm -rf /etc/nginx/conf.d/* /etc/supervisor/conf.d/*
cp -rf /docker/nginx/scriber.conf /etc/nginx/conf.d/
cp -rf /docker/supervisor/supervisord.conf /etc/supervisor/supervisord.conf
jinja2 /docker/supervisor/conf.d/scriber.j2 -o /etc/supervisor/conf.d/scriber.conf

ln -snf /data/data/files /opt/scriber/data/files
ln -snf /data/data/export_answer_data /opt/scriber/data/export_answer_data
ln -snf /data/data/prompter /opt/scriber/data/prompter
ln -snf /data/data/tbl_headers /opt/scriber/data/tbl_headers
ln -snf /data/data/training_cache /opt/scriber/data/training_cache
inv db.upgrade

if [ -n "${SUBPATH}" ]; then
  sed -i "s@rewrite\ \^(/scriber)@rewrite \^(${SUBPATH})@g" /etc/nginx/conf.d/scriber.conf
  sed -i "s@~\^(/scriber)@~\^(${SUBPATH})@g" /etc/nginx/conf.d/scriber.conf
fi

# post init process
if [ -z "${SKIP_SCHEMA_OVERWRITE}" ]; then
  while IFS= read -r line; do
    sh -c "$line"
  done <<<"$(read_config_with_jq -r '.build.docker.cli_pipe[]')"
fi


# k8s log
if [[ ! ("${ENABLE_STDOUT_LOG}" == "true" || (-n "${KUBERNETES_SERVICE_HOST}" && "${DISABLE_K8S_LOG}" != "true")) ]]; then
  exec 1>>/data/logs/init.log 2>&1
fi

# 清理旧的 celery beat 文件
rm -f /data/tmp/celerybeat*

# supervisord
exec supervisord -n -c /etc/supervisor/supervisord.conf
