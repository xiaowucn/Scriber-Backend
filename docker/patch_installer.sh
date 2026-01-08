#!/bin/bash

set -e

if [[ "$(id -u)" == '0' ]]; then
  exec gosu scriber "/docker/patch_installer.sh" "$@"
  exit $?
fi

_scriber_work_dir="/opt/scriber/"
test -f "${_scriber_work_dir}.version" || exit 0
_patch_work_dir="/tmp/scriber_patch/"
_patch_path="/data/patch/patch_$(cat ${_scriber_work_dir}.version).tar.gz"
_supervisor_sock="/dev/shm/supervisor.sock"

_exit() {
  _exit_code=$?
  if [[ "$_exit_code" -lt 0 ]]; then
    echo "[ERROR] install patch ${_patch_path} failed !!!"
  fi
  rm -rf ${_patch_work_dir}
  exit "${_exit_code}"
}

trap _exit HUP INT EXIT TERM QUIT

if [[ -f "${_patch_path}" ]]; then
  echo "[INFO] scriber patch package found to start install patch ..."
  mkdir -p "${_patch_work_dir}"
  tar -xf "${_patch_path}" -C "${_patch_work_dir}"
  chown -R $(id -u) "${_patch_work_dir}"

  if [ -d "${_patch_work_dir}"/pypi ]; then
    echo "start install ${_patch_work_dir}/pypi ..."
    export HOME=/tmp/
    if ! pip install "${_patch_work_dir}"/pypi/* --force-reinstall --no-deps --user; then
      echo "install ${_patch_work_dir}/pypi failed !!!"
      exit 1
    else
      echo "install ${_patch_work_dir}/pypi success ..."
      rm -rf "${_patch_work_dir}"/pypi
    fi
  fi

  cp -rf "${_patch_work_dir}"/* "${_scriber_work_dir}"

  if [[ -e "${_supervisor_sock}" ]]; then
    echo "[INFO] restarting services ..."
    supervisorctl restart all >/dev/null 2>&1
  fi
  echo "[INFO] patch install success ..."
else
  echo "[INFO] no patch package found in ${_patch_path}, do nothing ..."
fi
