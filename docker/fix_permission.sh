#!/bin/bash

find /opt/scriber/ /opt/fonts/ /data/ /docker/supervisor/ /docker/nginx/ -type d -exec chmod 777 '{}' \;
find /opt/scriber/ /opt/fonts/ /data/ /docker/supervisor/ /docker/nginx/ -type f -exec chmod 666 '{}' \;

chmod 777 /etc/nginx/ /etc/supervisor/
chmod 777 -R /etc/nginx/conf.d/ /etc/supervisor/conf.d/
chmod 666 /etc/nginx/nginx.conf /etc/supervisor/supervisord.conf || true
chmod 755 /opt/scriber/bin/pdf2svg /opt/scriber/bin/dr/docx_revision || true
chmod 755 /docker/docker-entrypoint.sh /docker/patch_installer.sh /docker/healthcheck.pyc || true
