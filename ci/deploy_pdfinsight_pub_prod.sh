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

# [b1] scriber-pdfinsight-hkex.b1.cheftin.cn:1080
echo "download scriber hkex prod pdfinsight image ..."
run ssh ci@100.64.0.17 "docker pull registry.cheftin.cn/p/${PDFINSIGHT_IMAGE_NAME}"

# sed
run ssh ci@100.64.0.17 "sed -i -r '1,50s@pdfinsight:.{5,10}@${PDFINSIGHT_IMAGE_NAME}@' /data/scriber_pdfinsight_prod/docker-compose.yml"

# up
run ssh ci@100.64.0.17 "docker-compose -f /data/scriber_pdfinsight_prod/docker-compose.yml up -d"

# mm
if [ -f "/data/ci/fitout/autodoc/send_mm_msg.sh" ]; then
    bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[通用类型PDFInsight正式环境\(1080\)\]\(scriber-pdfinsight-public.b1.cheftin.cn:1080\)\ 已更新至版本\:\`${PDFINSIGHT_IMAGE_NAME}\`
fi
