#!/usr/bin/env bash

set -ex
. ci/environment

_exit() {
  EXIT_CODE=$?

  set +e

  if [ $EXIT_CODE -ne 0 ]; then
    if [ -f "/data/ci/fitout/common/get_commit_users.py" ]; then
      MENTION_USERS=$(python3 /data/ci/fitout/common/get_commit_users.py)
    fi
    if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
      GO_LOG_URL="https://gocd.paodingai.com/go/tab/build/detail/${GO_PIPELINE_NAME}/${GO_PIPELINE_COUNTER}/${GO_STAGE_NAME}/${GO_STAGE_COUNTER}/${GO_JOB_NAME}"
      bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber "| 代码提交人 | 错误信息 | 构建日志地址 |\n| --- | --- | --- |\n| :facebug: **${MENTION_USERS}** | :x: **Scriber Unit Test** | :point_right: [*click the jump*](${GO_LOG_URL}) |"
    fi
  fi
  # delete db docker images
  docker rm -f scriber_unittest_pg scriber_unittest_redis || true
  exit $EXIT_CODE

}

trap _exit INT EXIT QUIT TERM HUP

if [ -n "${VENV_PATH}" ]; then
  source ${VENV_PATH}/bin/activate
  pip install --upgrade --no-cache-dir uv pip
  uv sync --group dev --active
fi

# run db docker images
docker rm -f scriber_unittest_pg scriber_unittest_redis || true

# set db data info
export ENV=dev
export SCRIBER_CONFIG_DB_HOST=127.0.0.1
export SCRIBER_CONFIG_DB_DBNAME=scriber_test
# shellcheck disable=SC2155
export SCRIBER_CONFIG_DB_PORT=$(get_unused_port)
if [[ "${UNIT_DB}" == "PG" ]]; then
  docker run -d -p "${SCRIBER_CONFIG_DB_PORT}":5432 --name=scriber_unittest_pg -e POSTGRES_DB=scriber_test -e POSTGRES_HOST_AUTH_METHOD=trust registry.cheftin.cn/p/postgres16_pd
elif [[ "${UNIT_DB}" == "GAUSS" ]]; then
  export SCRIBER_CONFIG_DB_USER=gaussdb
  export SCRIBER_CONFIG_DB_PASSWORD=Scriber@123456
  export SCRIBER_CONFIG_DB_SERVER_SETTINGS_APPLICATION_NAME="Scriber(openGaussDB)"
  docker run -d --privileged -p "${SCRIBER_CONFIG_DB_PORT}":5432 --name=scriber_unittest_pg -e TZ=Asia/Shanghai -e LANG=en_US.utf8 -e GS_DB=scriber_test -e GS_PASSWORD=Scriber@123456 enmotech/opengauss
else
  echo "Environment variable UNIT_DB cannot be empty，Please configure it."
  exit 1
fi

export SCRIBER_CONFIG_REDIS_HOST=127.0.0.1
export SCRIBER_CONFIG_REDIS_PASSWORD=scriber
# shellcheck disable=SC2155
export SCRIBER_CONFIG_REDIS_PORT=$(get_unused_port)
docker run -d -p "${SCRIBER_CONFIG_REDIS_PORT}":6379 --name=scriber_unittest_redis redis redis-server --requirepass scriber

# upgrade db revision
inv db.upgrade

# restore tests file
git restore tests

# run unit test
pytest -vv