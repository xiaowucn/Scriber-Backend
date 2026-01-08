#!/bin/bash

run() {
  "$@"
  _exit_code=$?
  if [ ${_exit_code} -ne 0 ]; then
    echo "Error: exec "$@" with exit code ${_exit_code}"
    exit ${_exit_code}
  fi
}

# deploy bohr ==> scriber completeness zjs for autodoc ==> http://100.64.0.15:1600
WORK_DIR=$(pwd)
run rsync -av --delete ../Scriber/dist/ /data1/scriber_prompter_zjs/Scriber-Frontend/dist/
run rsync -av --exclude=/data/files --exclude=/data/prompter --exclude=.git ./ /data1/scriber_prompter_zjs/Scriber-Backend/

run /home/cheftin/.pyenv/versions/draft_competeness_zjs/bin/pip install --upgrade --no-cache-dir -r /data1/scriber_prompter_zjs/Scriber-Backend/misc/requirements.txt

cd /data1/scriber_prompter_zjs/Scriber-Backend/
source /home/cheftin/.pyenv/versions/draft_competeness_zjs/bin/activate
source ci/environment
run /home/cheftin/.pyenv/versions/draft_competeness_zjs/bin/alembic -c misc/alembic.ini -n db -x dburl=postgresql+psycopg2://postgres:@127.0.0.1:35331/draft upgrade head
run sudo supervisorctl restart scriber-completeness-zjs-web scriber-completeness-zjs-worker scriber-completeness-zjs-worker-trainning

cd ${WORK_DIR}
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
  if [ -d .git ]; then
    BRANCH_NAME="($(git rev-parse --abbrev-ref HEAD))"
  fi

  bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[Scriber\ completeness测试环境\(1600\)\]\(http://100.64.0.15:1600\)后端已更新至版本\:\`${GO_REVISION_ANSWER_VERSION_UPDATE:0:8}${BRANCH_NAME}\`
fi
