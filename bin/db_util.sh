#!/usr/bin/env bash

PROJECT_ROOT=$(dirname $(
  cd $(dirname "$0")
  pwd
))
DATA_DIR=${PROJECT_ROOT}/data/pg_data
ExitCode=0

# NOTE: Pay attention to the PATH variable
#       It is important to set the correct path to the postgresql binaries first
#       otherwise this script will not work as expected
if [ -d /usr/pgsql-10/bin ]; then
  export PATH=/usr/pgsql-10/bin:$PATH
elif [ -d /usr/lib/postgresql/10/bin ]; then
  export PATH=/usr/lib/postgresql/10/bin:$PATH
elif [ -d /usr/lib/postgresql/9.6/bin ]; then
  export PATH=/usr/lib/postgresql/9.6/bin:$PATH
elif [ -d /usr/local/pgsql/bin ]; then
  export PATH=/usr/local/pgsql/bin:$PATH
fi

rm "${PROJECT_ROOT}"/config/config-test.yml >/dev/null 2>&1
source "${PROJECT_ROOT}"/ci/environment

get_config() {
  pushd "${PROJECT_ROOT}" >/dev/null 2>&1
  RESULT=$(python3 -c "from remarkable.config import get_config; print(get_config('$1') or \"\")" 2>/dev/null)
  popd >/dev/null 2>&1
  echo "${RESULT}"
}

DB_USER=$(get_config "db.user")
DB_NAME=$(get_config "db.dbname")
DB_PORT=$(get_config "db.port")
DB_HOST=$(get_config "db.host")
DB_PASSWORD=$(get_config "db.password")
DB_SCHEMA=$(get_config "db.schema")

export PGOPTIONS="-c search_path=${DB_SCHEMA}"

change_passwd() {
  echo "alter user ${DB_USER} with password '${DB_PASSWORD}';" | psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}"
}

create_db() {
  echo "create database ${DB_NAME}"
  echo "create database ${DB_NAME} encoding='utf-8' template=template0;" | PGPASSWORD="${DB_PASSWORD}" psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}"
  echo "CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA};" | PGPASSWORD="${DB_PASSWORD}" psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}" -d "${DB_NAME}"
}

drop_db() {
  echo "drop database ${DB_NAME}"
  echo "drop database ${DB_NAME};" | PGPASSWORD="${DB_PASSWORD}" psql -U "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}"
}

start() {
  pg_ctl start -D "${DATA_DIR}" -l "${DATA_DIR}"/postgresql.log -o "-p ${DB_PORT} --unix_socket_directories=${DATA_DIR}"
}

stop() {
  pg_ctl stop -D "${DATA_DIR}" -o "-p ${DB_PORT} --unix_socket_directories=${DATA_DIR}" -m fast
}

init() {
  initdb -D "${DATA_DIR}"
  start
  echo "wait 2 seconds..."
  sleep 2
  createuser -s "${DB_USER}" -h "${DB_HOST}" -p "${DB_PORT}"
  create_db
  change_passwd
}

write_test_config() {
  cat <<EOF >"${PROJECT_ROOT}"/config/config-test.yml
db:
  host: "${DB_HOST}"
  port: "${DB_PORT}"
  dbname: "${DB_NAME}"
  user: "${DB_USER}"
  password: "${DB_PASSWORD}"
redis:
  db: 11
EOF
}

test_case() {
  case "$1" in
  up)
    write_test_config
    create_db
    inv db.flush-rdb
    inv db.upgrade
    ;;
  down)
    write_test_config
    drop_db
    inv db.flush-rdb
    rm "${PROJECT_ROOT}"/config/config-test.yml >/dev/null 2>&1
    ;;
  *)
    echo "Usage: $0 test {up|down} [db_name]"
    ;;
  esac

}

case "$1" in
init)
  init
  ;;
start)
  start
  ;;
stop)
  stop
  ;;
restart)
  stop
  start
  ;;
create_db)
  create_db
  change_passwd
  ;;
test)
  [ "x$(echo "${DB_NAME}" | awk -F '_' '{print $NF}')" = "xtest" ] || DB_NAME="${3:-"${DB_NAME}"}"_test
  test_case "${2:-"up"}"
  ;;
console)
  PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -d ${DB_NAME} -U ${DB_USER}
  if [ $? -ne 0 ]; then
    echo "Failed to connect to database ${DB_NAME}"
    psql "host=${DB_HOST} port=${DB_PORT} user=${DB_USER} password=${DB_PASSWORD}"
  fi
  ;;
sql)
  PGPASSWORD=${DB_PASSWORD} psql "host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER}" -c "${2:-"select version()"}"
  if [ $? -ne 0 ]; then
    echo "Failed to connect to database ${DB_NAME}"
    PGPASSWORD=${DB_PASSWORD} psql "host=${DB_HOST} port=${DB_PORT} user=${DB_USER}" -c "${2:-"select version()"}"
  fi
  ;;
redis)
  REDIS_HOST=$(get_config "redis.host")
  REDIS_PORT=$(get_config "redis.port")
  REDIS_DB=$(get_config "redis.db")
  REDISCLI_AUTH=$(get_config "redis.password")
  if [ "x${REDISCLI_AUTH}" != "x" ]; then
    REDISCLI_AUTH="${REDISCLI_AUTH}" redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" -n "${REDIS_DB}"
  else
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" -n "${REDIS_DB}"
  fi
  ;;
*)
  echo "Usage: $0 {init|create_db|start|stop|restart|test|console|redis|sql}"
  ExitCode=1
  ;;
esac

exit ${ExitCode}
