#!/bin/bash

set -x

run() {
  "$@"
  _exit_code=$?
  if [ ${_exit_code} -ne 0 ]; then
    echo "Error: exec "$@" with exit code ${_exit_code}"
    exit ${_exit_code}
  fi
}

# deploy bohr ==> scriber test ==> http://bohr.cheftin.cn:4085
WORK_DIR=$(pwd)
run rsync -av --delete ../dist/dist/scriber_front/dist/ /data/scriber_prompter/dist/
run rsync -av --exclude=.git ./ /data/scriber_prompter/Scriber-Backend/

run /home/docker_test/.pyenv/versions/scriber_prompter/bin/pip install --upgrade --no-cache-dir -r /data/scriber_prompter/Scriber-Backend/misc/prod-requirements.txt

cd /data/scriber_prompter/Scriber-Backend/
. /home/docker_test/.pyenv/versions/scriber_prompter/bin/activate
run /home/docker_test/.pyenv/versions/scriber_prompter/bin/alembic -c misc/alembic.ini -n db -x dburl=postgresql+psycopg2://postgres:@127.0.0.1:35336/draft upgrade head
run sudo supervisorctl signal HUP draft-prompter-web
run sudo supervisorctl restart draft-prompter-worker draft-prompter-worker-trainning

# send messages
cd "${WORK_DIR}" || exit
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
  if [ -d .git ]; then
    BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
  fi

  bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[Scriber推荐答案测试环境\(4085\)\]\(http://bohr.cheftin.cn:4085\)已更新\:\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}${BRANCH_NAME}\`
fi
