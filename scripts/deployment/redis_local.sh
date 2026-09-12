#!/bin/sh
# Run from Linux/WSL with an explicit E:-backed runtime directory.
set -eu
action=${1:?usage: redis_local.sh build|start|status|stop RUNTIME_DIR}
runtime=${2:?runtime directory required}
case "$runtime" in /*) ;; *) echo 'Use an absolute data-drive path' >&2; exit 2 ;; esac
version=8.2.9
expected=531b314e5557ad76d941f605b3e3162ac61dc141f37c407e1f91fcfe17ea8c30
source_dir="$runtime/redis-$version"
case "$action" in
  build)
    mkdir -p "$runtime/downloads" "$runtime/redis-build-tmp"
    archive="$runtime/downloads/redis-$version.tar.gz"
    if [ ! -f "$archive" ]; then
      curl --fail --location "https://download.redis.io/releases/redis-$version.tar.gz" --output "$archive"
    fi
    printf '%s  %s\n' "$expected" "$archive" | sha256sum --check --status
    if [ ! -d "$source_dir" ]; then tar -xzf "$archive" -C "$runtime"; fi
    TMPDIR="$runtime/redis-build-tmp" make -C "$source_dir" -j4 MALLOC=libc BUILD_TLS=yes
    ;;
  start)
    if "$source_dir/src/redis-cli" -p 16379 ping >/dev/null 2>&1; then
      echo 'Port 16379 already in use; refusing a duplicate start' >&2; exit 1
    fi
    mkdir -p "$runtime/redis-data"
    "$source_dir/src/redis-server" --bind 127.0.0.1 --port 16379 --daemonize yes \
      --dir "$runtime/redis-data" --appendonly yes --maxmemory 64mb --maxmemory-policy noeviction \
      --pidfile "$runtime/redis.pid" --logfile "$runtime/redis.log"
    # Readiness can lag daemonization; bounded polling avoids a false failure.
    attempt=0
    until "$source_dir/src/redis-cli" -p 16379 ping; do
      attempt=$((attempt + 1)); [ "$attempt" -lt 5 ] || exit 1; sleep 1
    done
    ;;
  status) "$source_dir/src/redis-cli" -p 16379 ping ;;
  stop)
    actual=$("$source_dir/src/redis-cli" -p 16379 --raw CONFIG GET dir | tail -n 1 | tr -d '\r')
    [ "$actual" = "$runtime/redis-data" ] || { echo 'Redis data-directory ownership mismatch' >&2; exit 1; }
    "$source_dir/src/redis-cli" -p 16379 SHUTDOWN SAVE
    ;;
  *) echo 'Unknown lifecycle action' >&2; exit 2 ;;
esac
