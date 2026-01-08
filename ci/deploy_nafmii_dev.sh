#!/bin/bash
set -ex

# exit
run() {
    "$@"
    _exit_code=$?
    if [ ${_exit_code} -ne 0 ]; then
        echo "Error: exec "$@" with exit code ${_exit_code}"
        exit ${_exit_code}
    fi
}

# lfs
run ci/check_work_dir.sh
run git lfs pull

# frontend
#run rsync -avz --progress --exclude=.git --delete ../Scriber/dist*/* ./remarkable/static/

# backend
run rsync -avz --progress --delete --safe-links \
  --exclude=/data/export_answer_data --exclude=/data/files \
  --exclude=/data/prompter --exclude=/data/training_cache --exclude=/error_reports \
  --exclude=/data/tbl_headers --exclude=/healthcheck.py --exclude=/.version --exclude=/i18n/**.po --exclude=/i18n/**.pot \
  --exclude=/remarkable/static  ./ /data/nafmii_test/scriber_nafmii_dev/code_src/Scriber-Backend/


# git
cd /data/nafmii_test/scriber_nafmii_dev/code_src/Scriber-Backend
run echo "${GO_REVISION_SCRIBER_BACKEND:0:8}" >.git_revision
run echo "${GO_MATERIAL_BRANCH_SCRIBER_BACKEND}" >>.git_revision

# restart
run docker exec -i scriber_nafmii_demo_web ./docker/deploy_upgrade.sh

# mm
bash /data/ci/fitout/autodoc/send_mm_msg.sh \
    http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa \
    scriber \[Scriber交易商协会开发环境\(22100\)\]\(http://100.64.0.11:22100/\)已更新\:\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}\(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND}\)\`
