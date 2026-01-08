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

WORK_DIR=$(pwd)

# deploy xa1 ==> ht new test ==> http://100.64.0.15:1201
cd "${WORK_DIR}" || exit
run rsync -avz --progress --delete ../dist_ht/dist_ht/scriber_front/dist_ht/ /data/scriber_ht_test_old/Scriber-HT/
run rsync -av --exclude=/data/files --exclude=/data/pg_data --exclude=.git ./ /data/scriber_ht_test_old/Scriber-Backend/
run /home/cheftin/.pyenv/versions/scriber_ht/bin/pip install --upgrade --no-cache-dir -r /data/scriber_ht_test_old/Scriber-Backend/misc/prod-requirements.txt

cd /data/scriber_ht_test_old/Scriber-Backend/ || exit
. /home/cheftin/.pyenv/versions/scriber_ht/bin/activate
run source ci/environment
run export PYTHONPATH=./
run /home/cheftin/.pyenv/versions/scriber_ht/bin/alembic -c misc/alembic.ini -n db -x dburl=postgresql+psycopg2://postgres:scriberht@127.0.0.1:12081/draft upgrade head
run sudo supervisorctl restart draft-ht-test-web-old draft-ht-test-worker-old draft-ht-test-worker-trainning-old

# etcd
GO_SCRIBER_FRONT_COMMIT=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_COMMIT --print-value-only)
GO_SCRIBER_FRONT_BRANCH=$(ETCDCTL_API=3 etcdctl --user=ci:appwillgoogle --endpoints=100.64.0.1:2379 get GO_SCRIBER_FRONT_BRANCH --print-value-only)

# send messages
cd "${WORK_DIR}" || exit
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
    if [ -d .git ]; then
        BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
    fi

    if [ -d ../Scriber-HT/.git ]; then
        cd ../Scriber-HT || exit
        HT_FRONT_BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
        cd - || exit
    fi

    bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa haitong-contract \[Scriber\ ht测试环境\(1201\)]\(http://100.64.0.15:1201\)已更新\:\ \`前端\:${GO_SCRIBER_FRONT_COMMIT}\(${GO_SCRIBER_FRONT_BRANCH}\)\`\ \`后端\:${GO_REVISION_SCRIBER_BACKEND:0:8}\(${BRANCH_NAME}\)\`
fi
