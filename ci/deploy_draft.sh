#!/bin/bash

run() {
  "$@"
  _exit_code=$?
  if [ ${_exit_code} -ne 0 ]; then
    echo "Error: exec $* with exit code ${_exit_code}"
    exit ${_exit_code}
  fi
}

# deploy bohr ==> scriber1 test ==> http://100.64.0.1:4080
WORK_DIR=$(pwd)
echo "${GO_MATERIAL_BRANCH_SCRIBER_BACKEND}" >.git_revision
echo "${GO_REVISION_SCRIBER_BACKEND:0:8}" >>.git_revision

# shellcheck disable=SC2129
run rsync -av --exclude=/data/files --exclude=/data/pg_data --exclude=.git ./ docker_test@100.64.0.1:/data/scriber_test1/Scriber-Backend/

run ssh docker_test@bohr.cheftin.cn "docker exec -i scriber_ccxi_market_dev_web bash -c 'inv db.upgrade'"
run ssh -tt docker_test@bohr.cheftin.cn "docker exec -i scriber_ccxi_market_dev_web bash -c 'supervisorctl start all'"
run ssh -tt docker_test@bohr.cheftin.cn "docker exec -i scriber_ccxi_market_dev_web bash -c 'supervisorctl signal HUP scriber:'"

cd "${WORK_DIR}" || True
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
  if [ -d .git ]; then
    BRANCH_NAME="($(git rev-parse --abbrev-ref HEAD))"
  fi

  bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[Scriber测试环境\(4080\)\]\(http://100.64.0.1:4080\)\ 后端已更新至版本\:\`${GO_REVISION_SCRIBER_BACKEND:0:8}\(${GO_MATERIAL_BRANCH_SCRIBER_BACKEND}\)\`
fi
