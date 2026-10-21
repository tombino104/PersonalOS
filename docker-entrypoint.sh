#!/bin/sh
set -e

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_DIR"
  chown -R appuser "$DATA_DIR"
  exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
fi

exec "$@"
