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

# backend
run rsync -avz --progress --delete --safe-links \
  --exclude=remarkable/static \
  --exclude=/data/export_answer_data --exclude=/data/files \
  --exclude=/data/prompter --exclude=/data/training_cache --exclude=/error_reports \
  --exclude=/data/tbl_headers --exclude=/healthcheck.py --exclude=/.version --exclude=/i18n/**.po --exclude=/i18n/**.pot \
    ./ /data/scriber_csc_mark_test/code_src/Scriber-Backend/

# restart
run docker exec -i scriber_csc_mark_web ./docker/deploy_upgrade.sh

# mm
bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber "[Scriber(22102)-Scriber中信建投标注环境-后端-更新成功](http://100.64.0.3:22102)\`版本：${GO_REVISION_SCRIBER_BACKEND_MASTER:0:8}(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND_MASTER})\`"
