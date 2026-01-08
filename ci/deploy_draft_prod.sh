#!/bin/bash

set -x
set -e

# deploy jefferson ==> scriber prod ==> http://f.paodingai.com:8000
WORK_DIR=$(pwd)
rsync -av --delete ../dist/dist/scriber_front/dist/ ./remarkable/static/
rsync -av --exclude=/data/files --exclude=/data/pg_data --exclude=.git ./ scriber@47.92.38.232:/data/scriber/Scriber-Backend/

ssh -tt scriber@47.92.38.232 "sudo /etc/scriber_prod_backup.sh"

ssh scriber@47.92.38.232 "/home/scriber/.pyenv/versions/scriber_prod/bin/pip install --upgrade --no-cache-dir -r /data/scriber/Scriber-Backend/misc/prod-requirements.txt"

ssh scriber@47.92.38.232 "bash -c \"cd /data/scriber/Scriber-Backend && /home/scriber/.pyenv/versions/scriber_prod/bin/alembic -c misc/alembic.ini -n db -x dburl=postgresql+psycopg2://postgres:@127.0.0.1:35332/draft upgrade head\""
ssh -tt scriber@47.92.38.232 "sudo supervisorctl signal HUP draft-prod-web"
ssh -tt scriber@47.92.38.232 "sudo supervisorctl restart draft-prod-worker draft-prod-worker-trainning"

# send messages:w

cd "${WORK_DIR}"
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
    if [ -d .git ]; then
        BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
    fi

    bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[Scriber内部测试环境\(f.paodingai.com:8000\)\]\(http://f.paodingai.com:8000\)已更新\:\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}${BRANCH_NAME}\`
fi
