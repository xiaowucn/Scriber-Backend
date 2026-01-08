#!/bin/bash

set -ex

run() {
    "$@"
    _exit_code=$?
    if [[ ${_exit_code} -ne 0 ]]; then
        echo "Error: exec "$@" with exit code ${_exit_code}"
        exit ${_exit_code}
    fi
}

# env
PDFINSIGHT_VERSION="${GO_DEPENDENCY_LABEL_BUILD_PDFINSIGHT_AUTODOC}"
PDFINSIGHT_IMAGE_NAME="pdfinsight:$((PDFINSIGHT_VERSION / 1000)).$(((PDFINSIGHT_VERSION % 1000) / 100)).$((PDFINSIGHT_VERSION % 100))"

# [c5] 100.64.0.6:54000
echo "download scriber hkex prod pdfinsight image ..."
run ssh ci@100.64.0.6 "docker pull registry.cheftin.cn/p/${PDFINSIGHT_IMAGE_NAME}"

# sed
run ssh ci@100.64.0.6 "sed -i -r '1,50s@pdfinsight:.{5,10}@${PDFINSIGHT_IMAGE_NAME}@' /data2/scriber_pdfinsight_test/docker-compose.yml"

# up
run ssh ci@100.64.0.6 "docker-compose -f /data2/scriber_pdfinsight_test/docker-compose.yml up -d"

# mm
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
    bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[通用类型PDFInsight测试环境\(54000\)\]\(100.64.0.6:54000\)\ 已更新至版本\:\`${PDFINSIGHT_IMAGE_NAME}\`
fi
