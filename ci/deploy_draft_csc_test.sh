#!/bin/bash

set -x
set -e

# deploy c4 ==> csc ==> http://bj.cheftin.cn:44003
WORK_DIR=$(pwd)
export PATH="/home/ci/.pyenv/versions/csc_dev/bin:$PATH"

rsync -avz --progress --delete ../dist_csc/dist_csc/scriber_front/dist_csc/ /data/scriber_csc_demo/backup/code_src/Scriber-Frontend/dist/
rsync -avz --progress --exclude=/data/files --exclude=/data/prompter --exclude=/extract_ipo_tables --exclude=.git ./ /data/scriber_csc_demo/backup/code_src/Scriber-Backend

/home/ci/.pyenv/versions/csc_dev/bin/pip install --upgrade --no-cache-dir -r /data/scriber_csc_demo/backup/code_src/Scriber-Backend/misc/prod-requirements.txt

cd /data/scriber_csc_demo/backup/code_src/Scriber-Backend
. /home/ci/.pyenv/versions/csc_dev/bin/activate
/home/ci/.pyenv/versions/csc_dev/bin/alembic -c misc/alembic.ini -n db -x dburl=postgresql+psycopg2://postgres:@172.20.3.3:5432/scriber upgrade head
sudo supervisorctl signal HUP draft-csc-test-web
sudo supervisorctl restart draft-csc-test-worker draft-csc-test-worker-trainning

# etcd
GO_SCRIBER_FRONT_COMMIT=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_COMMIT --print-value-only)
GO_SCRIBER_FRONT_BRANCH=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_BRANCH --print-value-only)

# sendmm
cd "${WORK_DIR}"
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
  if [ -d .git ]; then
    BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
  fi

  bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[Scriber中信建投测试环境\(44003\)\]\(http://bj.cheftin.cn:44003\)已更新\:\ \`前端\:${GO_SCRIBER_FRONT_COMMIT}\(${GO_SCRIBER_FRONT_BRANCH}\)\`\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}${BRANCH_NAME}\`
fi
