#!/usr/bin/env bash

set -x

if [ -n "${VENV_PATH}" ]; then
    source ${VENV_PATH}/bin/activate
    pip install --upgrade --no-cache-dir uv
    uv sync --group dev --active
fi

source ci/environment
./docker/cyc .src
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    if [ -f "/data/ci/fitout/common/get_commit_users.py" ]; then
        MENTION_USERS=$(python3 /data/ci/fitout/common/get_commit_users.py)
    fi
    if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
        GO_LOG_URL="https://gocd.paodingai.com/go/tab/build/detail/${GO_PIPELINE_NAME}/${GO_PIPELINE_COUNTER}/${GO_STAGE_NAME}/${GO_STAGE_COUNTER}/${GO_JOB_NAME}"
        bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber "| 代码提交人 | 错误信息 | 构建日志地址 |\n| --- | --- | --- |\n| :facebug: *${MENTION_USERS}* | :x: **Scriber CYC Error** | :point_right: [*click the jump*](${GO_LOG_URL}) |"
    fi
fi
exit $EXIT_CODE
