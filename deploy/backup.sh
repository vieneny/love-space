#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repo_root/deploy/.env"
backup_root="$repo_root/deploy/backups"
quiesce=false

usage() {
  cat <<'USAGE'
用法：bash deploy/backup.sh --quiesce-api [--env-file PATH] [--output DIR]
仅在实际 Linux 部署主机运行。会暂停本 Compose 的单个 API，导出数据库并只读归档照片，再恢复 API。
不购买资源，不自动上传或删除旧备份。备份包含私人数据，需要加密离机保存。
USAGE
}

while (($#)); do
  case "$1" in
    --quiesce-api) quiesce=true; shift ;;
    --env-file|--output)
      if (($# < 2)); then usage >&2; exit 1; fi
      if [[ "$1" == --env-file ]]; then env_file="$2"; else backup_root="$2"; fi
      shift 2 ;;
    --help) usage; exit 0 ;;
    *) usage >&2; exit 1 ;;
  esac
done
if [[ "$quiesce" != true ]]; then usage >&2; exit 1; fi
if [[ ! -f "$env_file" ]]; then printf '%s\n' '缺少生产环境文件。' >&2; exit 1; fi
for command in docker tar gzip sha256sum mktemp; do
  if ! command -v "$command" >/dev/null 2>&1; then printf '缺少命令：%s\n' "$command" >&2; exit 1; fi
done
compose=(docker compose --env-file "$env_file" -f "$repo_root/deploy/compose.yml")
"${compose[@]}" config --quiet
mkdir -p -- "$backup_root"
backup_root="$(cd -- "$backup_root" && pwd)"
lock_dir="$repo_root/deploy/backups/.backup.lock"
mkdir -p -- "${lock_dir%/*}"
if ! mkdir -- "$lock_dir"; then
  printf '%s\n' '备份锁已存在；确认没有其他备份进程后再手动清理锁目录。' >&2
  exit 1
fi

api_stopped=false
cleanup() {
  local status=$?
  trap - EXIT
  if [[ "$api_stopped" == true ]]; then
    if ! "${compose[@]}" start api >/dev/null; then
      printf '%s\n' 'API 恢复启动失败，请立即检查容器状态。' >&2
      status=1
    fi
  fi
  rmdir -- "$lock_dir" || true
  if ((status != 0)); then printf '%s\n' '备份未成功结束；隐藏的 .partial-* 目录不会被认定为完整备份，请检查后处理。' >&2; fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

api_id="$("${compose[@]}" ps --status running -q api)"
postgres_id="$("${compose[@]}" ps --status running -q postgres)"
if [[ -z "$api_id" || "$api_id" == *$'\n'* || -z "$postgres_id" || "$postgres_id" == *$'\n'* ]]; then
  printf '%s\n' '需要当前 Compose 中恰好一个正在运行的 API 和 PostgreSQL；不会启动原本停止的服务。' >&2
  exit 1
fi
api_image="$(docker inspect --format '{{.Image}}' "$api_id")"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
partial="$(mktemp -d "$backup_root/.partial-$stamp.XXXXXX")"
printf '%s\n' '暂停 API，阻止数据库和照片写入；此期间客户端会暂时不可用。'
api_stopped=true
"${compose[@]}" stop -t 30 api >/dev/null
"${compose[@]}" exec -T postgres pg_dump -U love_space -d love_space --format=custom > "$partial/database.dump"
# Reuse the locally built API image; do not run its command, migrations or network stack.
docker run --rm --network none --read-only --user 10001 \
  --volumes-from "$api_id:ro" --entrypoint tar "$api_image" \
  -C /app/data/media -czf - . > "$partial/media.tar.gz"
"${compose[@]}" exec -T postgres pg_restore --list < "$partial/database.dump" >/dev/null
tar -tzf "$partial/media.tar.gz" >/dev/null
printf 'format=1\ncreated_utc=%s\nconsistency=single-compose-api-stopped\nrestore_verified=false\n' "$stamp" > "$partial/manifest.txt"
(
  cd -- "$partial"
  sha256sum database.dump media.tar.gz manifest.txt > SHA256SUMS
  sha256sum --check --status SHA256SUMS
)
"${compose[@]}" start api >/dev/null
api_stopped=false
final="$backup_root/backup-$stamp-${partial##*.}"
mv -- "$partial" "$final"
printf '备份完成：%s\n' "$final"
printf '%s\n' '仅验证了归档可读与校验和，未执行恢复演练。请核验 API/HTTPS 恢复，并将完整备份加密复制到另一台设备。'
