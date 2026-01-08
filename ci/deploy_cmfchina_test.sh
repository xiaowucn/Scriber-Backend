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

# backend c121
run rsync -avz --progress --delete --safe-links \
  --exclude=remarkable/static \
  --exclude=/data/export_answer_data --exclude=/data/files \
  --exclude=/data/prompter --exclude=/data/training_cache \
  --exclude=/data/tbl_headers --exclude=/healthcheck.py --exclude=/.version --exclude=/i18n/**.po --exclude=/i18n/**.pot \
  ./ ci@100.64.0.10:/data2/scriber_cmfchina_test/code_src/Scriber-Backend/

# restart
run ssh ci@100.64.0.10 'docker exec -i scriber_cmfchina_test_web ./docker/deploy_upgrade.sh'

if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
  bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber "[Scriber(12119)-招商基金测试环境-后端-更新成功](http://100.64.0.10:12119)\`版本：${GO_REVISION_SCRIBER_BACKEND:0:8}(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND})\`"
fi
