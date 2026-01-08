#!/usr/bin/env bash

set -ex

run() {
    "$@"
    _exit_code=$?
    if [[ ${_exit_code} -ne 0 ]]; then
        echo "Error: exec $* with exit code ${_exit_code}"
        exit ${_exit_code}
    fi
}

# env
SCRIBER_VERSION="${IMAGE_NAME}:0.0.${GO_PIPELINE_COUNTER}"

# pull
run ssh ci@100.64.0.11 docker pull registry.cheftin.cn/p/"${SCRIBER_VERSION}"

# sed
run ssh ci@100.64.0.11 sed -ir "s@${IMAGE_NAME}:0.*@${SCRIBER_VERSION}@" /data/scriber_fullgoal/docker-compose.yaml

# up
run ssh ci@100.64.0.11 docker-compose -f /data/scriber_fullgoal/docker-compose.yaml up -d
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
    run bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \@xukaijing,@jinjin[富国基金scriber预发布更新成功\]\(http://100.64.0.11:51082\)
fi
