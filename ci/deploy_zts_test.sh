#!/bin/bash

set -ex

# exit
run() {
  "$@"
  _exit_code=$?
  if [ ${_exit_code} -ne 0 ]; then
    echo "Error: exec $* with exit code ${_exit_code}"
    exit ${_exit_code}
  fi
}

# backend c122
run rsync -avz --progress --delete --safe-links \
  --exclude=remarkable/static \
  --exclude=/data/export_answer_data --exclude=/data/files \
  --exclude=/data/prompter --exclude=/data/training_cache \
  --exclude=/data/tbl_headers --exclude=/healthcheck.py --exclude=/.version --exclude=/i18n/**.po --exclude=/i18n/**.pot \
  ./ ci@100.64.0.11:/data/scriber_zts_test/code_src/Scriber-Backend/

# restart
run ssh ci@100.64.0.11 'docker exec -i scriber_zts_test_web ./docker/deploy_upgrade.sh'

if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
  bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber "[Scriber-中泰证券测试环境-后端-更新成功](http://100.64.0.9:55845)\`版本：${GO_REVISION_SCRIBER_BACKEND:0:8}(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND})\`"
fi
