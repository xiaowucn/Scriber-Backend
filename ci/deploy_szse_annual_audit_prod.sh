#!/bin/bash

set -ex

# pre
if [[ ${SCRIBER_SZSE_ANNUAL_AUDIT_PROD} != "True" ]]; then
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

# frontend
run rsync -avz --progress --exclude=.git --delete ../dist_szse_ipo/dist_szse_ipo/scriber_front/dist_szse_ipo/ ./remarkable/static/

# backend
run rsync -avz --safe-links --delete \
  --exclude=/data/export_answer_data --exclude=/data/files \
  --exclude=/data/prompter --exclude=/data/training_cache \
  --exclude=/data/tbl_headers --exclude=/healthcheck.py --exclude=/.version --exclude=/i18n/**.po --exclude=/i18n/**.pot \
  ./ /data/scriber_szse_annual_audit_prod/code_src/Scriber-Backend/

# etcd
GO_SCRIBER_FRONT_COMMIT=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_COMMIT --print-value-only)
GO_SCRIBER_FRONT_BRANCH=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_BRANCH --print-value-only)

# restart
run docker exec -i scriber_szse_annual_audit_prod_web ./docker/deploy_upgrade.sh

# mm
bash /data/ci/fitout/autodoc/send_mm_msg.sh \
  http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa \
  scriber \[Scriber深交所年报合规审核内部正式环境\(46556\)\]\(http://100.64.0.5:46556/\)已更新\:\ \`前端\:${GO_SCRIBER_FRONT_COMMIT}\(${GO_SCRIBER_FRONT_BRANCH}\)\`\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}\(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND}\)\`
