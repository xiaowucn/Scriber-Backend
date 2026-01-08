#!/bin/bash
set -x
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

# frontend
run rsync -avz --progress --delete ../dist/dist/scriber_front/dist/ ./remarkable/static/

# backend
run rsync -avz --progress --delete --exclude=/data/export_answer_data --exclude=/data/files --exclude=/data/prompter --exclude=/data/training_cache --exclude=/data/tbl_headers --exclude=/healthcheck.py --exclude=/.version --exclude=/i18n/**.po --exclude=/i18n/**.pot ./ /data2/scriber_public_mark/code_src/Scriber-Backend

# etcd
GO_SCRIBER_FRONT_COMMIT=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_COMMIT --print-value-only)
GO_SCRIBER_FRONT_BRANCH=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_BRANCH --print-value-only)

# restart
run docker exec -i scriber_public_mark_web ./docker/deploy_upgrade.sh

# mm
bash /data/ci/fitout/autodoc/send_mm_msg.sh \
  http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa \
  scriber \[Scriber通用标注测试环境\]\(http://100.64.0.10:22100\)已更新\:\ \`前端\:${GO_SCRIBER_FRONT_COMMIT}\(${GO_SCRIBER_FRONT_BRANCH}\)\`\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}\(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND}\)\`
