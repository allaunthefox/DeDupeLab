#!/usr/bin/env zsh
set -euo pipefail
: > /home/allaun/rclone_debug.log

echo "RCLONE DEBUG LOG - dry-run - $(date -u)" >> /home/allaun/rclone_debug.log

echo "\n=== lsd Gdrive: (top-level) ===\n" >> /home/allaun/rclone_debug.log
rclone lsd Gdrive: --log-level DEBUG 2>&1 >> /home/allaun/rclone_debug.log || true

cmds=(
  "rclone move Gdrive:Documents Gdrive:Active/Documents --dry-run --log-level DEBUG"
  "rclone move \"Gdrive:Documents／General／\" Gdrive:Active/Documents --dry-run --log-level DEBUG"
  "rclone move Gdrive:Personal Gdrive:Active/Personal --dry-run --log-level DEBUG"
  "rclone move Gdrive:Backups Gdrive:Archives/Backups --dry-run --log-level DEBUG"
  "rclone move \"Gdrive:Archives／Backups／\" Gdrive:Archives/Backups --dry-run --log-level DEBUG"
  "rclone move Gdrive:HelloFax Gdrive:Inbox --dry-run --log-level DEBUG"
  "rclone move \"Gdrive:Uncategorized／\" Gdrive:Inbox/Uncategorized-ToSort --dry-run --log-level DEBUG"
  "rclone purge Gdrive:Music-backup --dry-run --log-level DEBUG"
  "rclone purge Gdrive:Entertainment --dry-run --log-level DEBUG"
)

for c in "${cmds[@]}"; do
  echo "\n=== COMMAND: $c ===\n" >> /home/allaun/rclone_debug.log
  eval $c 2>&1 >> /home/allaun/rclone_debug.log || true
done


echo "\n=== tree Gdrive:Active (preview) ===\n" >> /home/allaun/rclone_debug.log
rclone tree Gdrive:Active --log-level DEBUG 2>&1 | sed -n '1,200p' >> /home/allaun/rclone_debug.log || true


echo "\nRCLONE DRY-RUN COMPLETE - $(date -u)" >> /home/allaun/rclone_debug.log
