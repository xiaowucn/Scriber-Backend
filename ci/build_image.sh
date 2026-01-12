#!/usr/bin/env bash

set -e
export DOCKER_BUILDKIT=1

PROJECT_ROOT=$(dirname $(
  cd $(dirname "$0")
  pwd
))

read_config_with_jq() {
  pushd "${PROJECT_ROOT}" >/dev/null 2>&1
  RESULT=$(python3 -c "import json; from remarkable.config import get_config; print(json.dumps(get_config('')))" 2>/dev/null | jq "$@" 2>/dev/null)
  popd >/dev/null 2>&1
  echo "${RESULT}"
}

check_image() {
  echo 'check image start ... '
  if [[ -f "/data/ci/fitout/common/print_image_not_clean_file.sh" ]]; then
    if ! /data/ci/fitout/common/print_image_not_clean_file.sh --image "${IMAGE_NAME}:${IMAGE_VERSION}"; then
      echo 'check image end, but have some problems ...'
      exit 1
    fi
  fi
  echo 'check image end, no problem ...'
  return 0
}

build_image() {
  if ! docker build --pull --build-arg env="${ENV:-docker}" --squash --no-cache --platform "linux/${TARGET_PLATFORM}" --tag="${IMAGE_NAME}:${IMAGE_VERSION}" .; then
    cho 'build images error ...'
    exit 1
  fi
}

update_cache() {
  if [[ -f '/data2/build_scriber_sse_cachedata/all_pdfinsight.tar.gz' ]]; then
    mkdir -pv cache_data
    cp -rf /data2/build_scriber_sse_cachedata/* cache_data
  else
    echo "no cache files need to be imported ..."
  fi
}

delete_converter() {
  rm -rf ./bin/converter && echo "delete converter tool ..."
}

update_front() {
  rm -rf remarkable/static/* || true
  mkdir -pv remarkable/static/

  cp -rf ../Scriber/dist*/* remarkable/static/ || true
  cp -rf ../dist*/dist*/scriber_front/dist*/* remarkable/static/ || true
}

push_registry() {
  echo 'push registry'
  if [[ -n "${REGISTRY_URL}" ]]; then
    docker rmi "${REGISTRY_URL}/${IMAGE_NAME}":0.0.$((GO_PIPELINE_COUNTER - 2)) || true
    docker tag "${IMAGE_NAME}:${IMAGE_VERSION}" "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_VERSION}"
    docker push "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_VERSION}"
  fi
}

if [[ $TARGET_PLATFORM == "arm64" && "$(arch)" == "x86_64" && ! -f "/proc/sys/fs/binfmt_misc/qemu-aarch64" ]]; then
  docker run --pull always --privileged --rm registry.cheftin.cn/hub/linuxkit/binfmt:v1.1.0
fi

TARGET_PLATFORM=${TARGET_PLATFORM:-arm64}
IMAGE_NAME=${IMAGE_NAME:-'scriber'}
IMAGE_VERSION="dev"
ENV=${ENV:=dev}

if [[ -n "${GO_PIPELINE_COUNTER}" ]]; then
  IMAGE_VERSION=0.0.${GO_PIPELINE_COUNTER}
  docker rmi "${IMAGE_NAME}":0.0.$((GO_PIPELINE_COUNTER - 2)) || true
fi

git lfs pull
ln -sf docker/Dockerfile ./
ln -sf docker/dockerignore ./.dockerignore

# add extra files
cat >>./.dockerignore <<EOF
$(read_config_with_jq -r '.build.docker.dot_ignore[]')
EOF

# add build version and git revision
echo "${ENV:-dev}_0.0.${GO_PIPELINE_COUNTER:-dev}" >.version
echo "${GO_MATERIAL_BRANCH_SCRIBER_BACKEND:-dev}_${GO_REVISION_SCRIBER_BACKEND:0:8}" >.git_revision

mkdir -pv remarkable/static
update_front
if [[ "${IMAGE_NAME}" == 'scriber_sse' ]]; then
  update_cache
fi
if [[ "${IMAGE_NAME}" != 'scriber_csc' ]]; then
  delete_converter
fi

sed -i s/^export\ CYC_SERVER=.\*/export\ CYC_SERVER=\""${CYC_SERVER}"\"/g docker/cyc

build_image
if [[ -z "${IMAGE_NO_PUSH}" ]]; then
  if check_image; then
    push_registry
  fi
fi
