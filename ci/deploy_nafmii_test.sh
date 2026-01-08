#!/bin/bash

set -ex

# pre
if [[ ${SCRIBER_NAFMII_TEST} != "True" ]]; then
  exit 0
fi

# exit
run() {
  "$@"
  _exit_code=$?
  if [ ${_exit_code} -ne 0 ]; then
    echo "Error: exec $* with exit code ${_exit_code}"
    exit ${_exit_code}
  fi
}

# git
run echo "${GO_REVISION_SCRIBER_BACKEND:0:8}" >.git_revision
run echo "${GO_MATERIAL_BRANCH_SCRIBER_BACKEND}" >>.git_revision

# frontend - yarn build
run rsync -avz --progress --exclude=.git --delete ../dist/dist/scriber_front/dist/ ./remarkable/static/

# sync
run rsync -avz --safe-links \
  --exclude=/data/export_answer_data --exclude=/data/files \
  --exclude=/data/prompter --exclude=/data/trainning_cache \
  ./ /data/scriber_nafmii_test/code_src/Scriber-Backend/

# etcd
GO_SCRIBER_FRONT_COMMIT=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_COMMIT --print-value-only)
GO_SCRIBER_FRONT_BRANCH=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_BRANCH --print-value-only)

# restart
run docker exec -i scriber_nafmii_test_web ./docker/deploy_upgrade.sh

# mm
bash /data/ci/fitout/autodoc/send_mm_msg.sh \
  http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa \
  scriber \[Scriber交易商协会测试环境\(44033\)\]\(http://100.64.0.5:44033/\)已更新\:\ \`前端\:${GO_SCRIBER_FRONT_COMMIT}\(${GO_SCRIBER_FRONT_BRANCH}\)\`\ \`后端\:${GO_REVISION_SCRIBER_BACKEND_MASTER:0:8}\(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND_MASTER}\)\`
