#!/bin/bash

set -x
set -e

# deploy c4 ==> csc ==> http://bj.cheftin.cn:44002
WORK_DIR=$(pwd)
export PATH="/home/ci/.pyenv/versions/csc/bin:$PATH"

rsync -av --delete ../Scriber/dist/ /data/scriber_csc_demo2/backup/code_src/Scriber-Frontend/dist/
rsync -av --exclude=/data/files --exclude=/data/prompter --exclude=/extract_ipo_tables --exclude=.git ./ /data/scriber_csc_demo2/backup/code_src/Scriber-Backend

/home/ci/.pyenv/versions/csc/bin/pip install --upgrade --no-cache-dir -r /data/scriber_csc_demo2/backup/code_src/Scriber-Backend/misc/prod-requirements.txt

cd /data/scriber_csc_demo2/backup/code_src/Scriber-Backend
. /home/ci/.pyenv/versions/csc/bin/activate
/home/ci/.pyenv/versions/csc/bin/alembic -c misc/alembic.ini -n db -x dburl=postgresql+psycopg2://postgres:@172.20.2.3:5432/scriber upgrade head
sudo supervisorctl signal HUP draft-csc-prod-web
sudo supervisorctl restart draft-csc-prod-worker draft-csc-prod-worker-trainning

cd "${WORK_DIR}"
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
  if [ -d .git ]; then
    BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
  fi

  bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[Scriber中信建投正式环境\(44002\)\]\(http://bj.cheftin.cn:44002\)已更新\:\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}${BRANCH_NAME}\`
fi
