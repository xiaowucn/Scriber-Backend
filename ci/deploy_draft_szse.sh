#!/bin/bash

set -x
set -e

# deploy jefferson ==> szse prod ==> https://szse.paodingai.com
WORK_DIR=$(pwd)
rsync -av --exclude=.git --delete ../dist_szse/dist_szse/scriber_front/dist_szse/ ./remarkable/static/
rsync -av --exclude=/data/files --exclude=/data/pg_data --exclude=.git ./ scriber@47.92.38.232:/data2/scriber_szse_prod

ssh -tt scriber@47.92.38.232 "sudo /etc/scriber_szse_backup.sh"

ssh scriber@47.92.38.232 "/home/scriber/.pyenv/versions/scriber_szse_prod/bin/pip install --upgrade --no-cache-dir -r /data2/scriber_szse_prod/misc/prod-requirements.txt"

ssh scriber@47.92.38.232 "bash -c \"cd /data2/scriber_szse_prod && /home/scriber/.pyenv/versions/scriber_szse_prod/bin/alembic -c misc/alembic.ini -n db -x dburl=postgresql+psycopg2://postgres:@127.0.0.1:35334/draft upgrade head\""
ssh -tt scriber@47.92.38.232 "sudo supervisorctl signal HUP draft-szse-web draft-szse-web2"
ssh -tt scriber@47.92.38.232 "sudo supervisorctl restart draft-szse-web2 draft-szse-worker draft-szse-worker-trainning"

# send messages
cd "${WORK_DIR}" || exit
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
    if [ -d .git ]; then
        BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
    fi

    bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[Scriber\ szse正式环境\(szse\)\]\(https://szse.paodingai.com\)已更新\:\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}${BRANCH_NAME}\`
fi
