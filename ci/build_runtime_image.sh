#!/usr/bin/env bash

set -e
set -o pipefail
export DOCKER_BUILDKIT=1

cleanup() {
  git restore .dockerignore
  git restore Dockerfile
}
trap cleanup EXIT INT TERM ERR

TARGET_PLATFORM=${TARGET_PLATFORM:-arm64}
IMAGE_NAME="scriber-runtime"
IMAGE_VERSION="latest"

ln -sf docker/runtime/Dockerfile ./
ln -sf docker/runtime/dockerignore ./.dockerignore


NGINX_VERSION=$(docker run --rm --pull always -q --platform "linux/${TARGET_PLATFORM}" harbor.wujiaxing.top/library/nginx:latest nginx -v 2>&1 | awk -F '/' '{print $2}')
if ! docker build --progress=plain --pull --squash --no-cache --platform "linux/${TARGET_PLATFORM}" \
  --build-arg NGINX_VERSION="${NGINX_VERSION}" --build-arg=ALL_PROXY="http://100.64.0.2:11080" \
  --build-arg=NO_PROXY='100.64.0.2,100.64.0.1,100.64.0.9,100.64.0.8,localhost,*.cn,pypi.tuna.tsinghua.edu.cn' \
  --tag=${IMAGE_NAME}-${TARGET_PLATFORM}:${IMAGE_VERSION} .; then
  echo 'build images error'
  exit 1
fi

if [ -n "${REGISTRY_URL}" ]; then
  docker tag "${IMAGE_NAME}-${TARGET_PLATFORM}:${IMAGE_VERSION}" "${REGISTRY_URL}/${IMAGE_NAME}-${TARGET_PLATFORM}:${IMAGE_VERSION}"
  docker push "${REGISTRY_URL}/${IMAGE_NAME}-${TARGET_PLATFORM}:${IMAGE_VERSION}"

  NEW_MANIFEST+=("${REGISTRY_URL}/${IMAGE_NAME}-${TARGET_PLATFORM}:${IMAGE_VERSION}")
  if ! command -v jq &> /dev/null; then
      echo "Error: 'jq' command not found. Please install jq." >&2
      exit 1
  fi
  if OTHER_DIGESTS=$(
    docker buildx imagetools inspect "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_VERSION}" --raw |
      jq -e -r --arg ARCH "$TARGET_PLATFORM" '.manifests[]|select(.platform.architecture != $ARCH)|"\(.platform.architecture) \(.digest)"'
  ); then
    while IFS= read -r LINE; do
      # amd64/arm64
      ARCH=$(echo "$LINE" | awk '{print $1}')
      DIGEST=$(echo "$LINE" | awk '{print $2}')
      NEW_MANIFEST+=("${REGISTRY_URL}/${IMAGE_NAME}-${ARCH}@${DIGEST}")
    done <<<"$OTHER_DIGESTS"
  fi

  docker buildx imagetools create -t "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_VERSION}" "${NEW_MANIFEST[@]}"
fi
