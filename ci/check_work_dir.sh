#!/usr/bin/env bash

# color
prompt() {
  case ${1} in
  "-s" | "--success")
    echo -e "\033[1;32m""${*/-s/}""\033[0m"
    ;; # Print success message
  "-e" | "--error")
    echo -e "\033[1;31m${*/-e/}\033[0m"
    ;; # Print error message
  "-w" | "--warning")
    echo -e "\033[1;33m${*/-w/}\033[0m"
    ;; # Print warning message
  "-i" | "--info")
    echo -e "\033[1;36m${*/-i/}\033[0m"
    ;; # Print info message
  *)
    echo -e "$@"
    ;;
  esac
}

WORKER_DIR=$(pwd)
BASE_DIR=$(basename $WORKER_DIR)

if [[ ${BASE_DIR} == "Scriber-Backend" ]]; then
  prompt -s ">>> INFO: WORKER_DIR is Scriber-Backend"
else
  prompt -e ">>> ERROR: WORKER_DIR isn't Scriber-Backend, please check"
  exit 1
fi