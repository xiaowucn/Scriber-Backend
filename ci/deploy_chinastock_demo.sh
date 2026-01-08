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

# backend c2
run rsync -avz --progress --delete --safe-links \
  --exclude=remarkable/static \
  --exclude=/data/export_answer_data --exclude=/data/files \
  --exclude=/data/prompter --exclude=/data/training_cache --exclude=/error_reports \
  --exclude=/data/tbl_headers --exclude=/healthcheck.py --exclude=/.version --exclude=/i18n/**.po --exclude=/i18n/**.pot \
  ./ ci@100.64.0.3:/data/scriber_chinastock_demo/code_src/Scriber-Backend

# restart
run run ssh ci@100.64.0.3 'docker exec -i scriber_chinastock_demo_web ./docker/deploy_upgrade.sh'
# mm
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
  bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber "[Scriber(22103)-银河证券测试环境-后端-更新成功](http://100.64.0.3:22103)\`版本：${GO_REVISION_SCRIBER_BACKEND_MASTER:0:8}(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND_MASTER})\`"
fi
