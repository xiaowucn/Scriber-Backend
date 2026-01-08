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

# frontend
run rsync -avz --progress --exclude=.git --delete ../Scriber/dist*/* ./remarkable/static/

# backend
run rsync -avz --progress --delete --safe-links \
  --exclude=/data/export_answer_data --exclude=/data/files \
  --exclude=/data/prompter --exclude=/data/training_cache --exclude=/error_reports \
  --exclude=/data/tbl_headers --exclude=/healthcheck.py --exclude=/.version --exclude=/i18n/**.po --exclude=/i18n/**.pot \
    ./ ci@aligpu-1:/data/ci/scriber_csc_mark_prod/code_src/Scriber-Backend/

# restart
run ssh ci@aligpu-1 'sudo docker exec -i scriber_csc_mark_prod_web ./docker/deploy_upgrade.sh'

# mm
sleep 5
bash /data/ci/fitout/autodoc/send_mm_msg.sh \
    http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa \
    scriber \[Scriber中信建投标注生产环境\]\(https://scriber-csc-mark.paodingai.com/\)已更新\:\ \`前端\:${GO_REVISION_SCRIBER:0:8}\(${GO_MATERIAL_BRANCH_SCRIBER}\)\`\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}\(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND}\)\`
