#!/bin/bash

set -ex

# deploy c4 ==> szse test ==> http://bj.cheftin.cn:44020
WORK_DIR=$(pwd)
SCRIBER_SZSE_IMAGE_NAME="registry.cheftin.cn/p/scriber_szse:0.0.${GO_PIPELINE_LABEL}"

# pull image
ssh -p 40022 ci@bj.cheftin.cn "docker pull ${SCRIBER_SZSE_IMAGE_NAME}"
ssh -p 40022 ci@bj.cheftin.cn "docker rm -f scriber_szse_demo"

# run image
ssh -p 40022 ci@bj.cheftin.cn \
    "docker run -d --name=scriber_szse_demo -p 4020:8000 \
        --network=scriber_demo \
        --ip=172.20.20.4 \
        -v /data/scriber_szse_demo/scriber:/data \
        -e ENABLE_GUNICORN=True \
        -e SCRIBER_WORKER_NUM=2 \
        -e SCRIBER_WORKER_TRAINING_NUM=1 \
        -e SCRIBER_CONFIG_WEB_DOMAIN='bj.cheftin.com:44020' \
        -e SCRIBER_CONFIG_APP_AUTH_PDFINSIGHT_URL='http://192.168.1.40:4000' \
        -e SCRIBER_CONFIG_APP_AUTH_TRIDENT_URL='http://bj.cheftin.com:55816' \
        -e SCRIBER_CONFIG_CLIENT_OCR_ENABLE=True \
        -e SCRIBER_CONFIG_CLIENT_OCR_SERVICE=aliyun \
        -e PDFPARSER_CONFIG_OCR_ALIYUN_APP_KEY=25979225 \
        -e PDFPARSER_CONFIG_OCR_ALIYUN_APP_SECRET=b9ff9829a22b492d20f6a94804e76e7d \
        -e PDFPARSER_CONFIG_OCR_ALIYUN_APP_CODE=7eae1570f9e042a18ed698bc22610eba \
        -e PDFPARSER_CONFIG_OCR_CACHE_TYPE=minio \
        -e PDFPARSER_CONFIG_MINIO_URL="bj.cheftin.cn:55950" \
        -e PDFPARSER_CONFIG_MINIO_ACCESS_KEY=xbFjTDx6r48bt7xD \
        -e PDFPARSER_CONFIG_MINIO_SECRET_KEY=EXpMYbqpER48T3YLOuPsdh3vrRkbHz9h \
        --add-host='redis:172.20.20.2' \
        --add-host='postgres:172.20.20.3' \
        ${SCRIBER_SZSE_IMAGE_NAME}"

# send messages
bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa scriber \[Scriber\ szse测试环境\(44020\)\]\(http://bj.cheftin.cn:44020\)已更新
