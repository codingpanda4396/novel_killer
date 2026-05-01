#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

required_files=(
  "README.md"
  "bible/00_story_bible.md"
  "bible/01_characters.md"
  "bible/02_power_system.md"
  "bible/03_style_guide.md"
  "bible/04_forbidden_rules.md"
  "outlines/00_full_outline.md"
  "outlines/01_volume_outline.md"
  "outlines/02_cold_start_0_80k.md"
  "outlines/chapter_queue.md"
  "progress/active_threads.md"
  "progress/chapter_summary.md"
  "progress/continuity_index.md"
  "progress/current_context.md"
  "progress/timeline.md"
  "progress/word_count.md"
  "progress/publishing_log.md"
  "prompts/00_build_current_context.md"
  "prompts/01_generate_scene_card.md"
  "prompts/02_generate_chapter_draft.md"
  "prompts/03_review_chapter.md"
  "prompts/04_rewrite_chapter.md"
  "prompts/05_update_record.md"
  "prompts/06_continuity_check.md"
  "prompts/07_next_chapter_planner.md"
)

required_dirs=(
  "bible"
  "chapters"
  "chapters/scene_cards"
  "chapters/drafts"
  "chapters/final"
  "chapters/records"
  "outlines"
  "progress"
  "prompts"
)

usage() {
  cat <<'EOF'
novelctl - novel0 production scaffold

Usage:
  scripts/novelctl.sh check
  scripts/novelctl.sh status
  scripts/novelctl.sh new-chapter <number> <title>
  scripts/novelctl.sh context-pack <number>

Commands:
  check                 Validate required directories and files.
  status                Show current repo production status.
  new-chapter N TITLE   Create empty workflow files for one chapter.
  context-pack N        Create a context packet for chapter N.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

chapter_num() {
  local raw="$1"
  [[ "$raw" =~ ^[0-9]+$ ]] || die "chapter number must be numeric"
  printf "%03d" "$raw"
}

chapter_label() {
  local n="$1"
  printf "第%s章" "$(chapter_num "$n")"
}

ensure_repo() {
  [[ -d "$ROOT_DIR/.git" ]] || die "not a git repo: $ROOT_DIR"
}

check_system() {
  local failed=0
  cd "$ROOT_DIR"

  for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
      printf 'OK dir  %s\n' "$dir"
    else
      printf 'MISS dir %s\n' "$dir"
      failed=1
    fi
  done

  for file in "${required_files[@]}"; do
    if [[ -s "$file" ]]; then
      printf 'OK file %s\n' "$file"
    else
      printf 'MISS file %s\n' "$file"
      failed=1
    fi
  done

  return "$failed"
}

status_system() {
  cd "$ROOT_DIR"
  printf '# novel0 status\n\n'
  printf 'Branch: '
  git branch --show-current 2>/dev/null || printf 'unknown'
  printf '\n'

  printf 'Historical chapter files: '
  find chapters -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' '
  printf '\n'

  printf 'Scene cards: '
  find chapters/scene_cards -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' '
  printf '\n'

  printf 'Drafts: '
  find chapters/drafts -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' '
  printf '\n'

  printf 'Final chapters: '
  find chapters/final -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' '
  printf '\n\n'

  printf 'Next required step:\n'
  printf '%s\n' '- Run prompt 00 to rebuild progress/current_context.md before producing any new chapter.'
  printf '%s\n' '- If current_context blocks production, fix outlines/progress first.'
}

write_if_missing() {
  local file="$1"
  local content="$2"
  if [[ -e "$file" ]]; then
    printf 'SKIP exists %s\n' "$file"
    return 0
  fi
  printf '%s\n' "$content" > "$file"
  printf 'CREATE %s\n' "$file"
}

new_chapter() {
  local number="$1"
  local title="${2:-}"
  [[ -n "$title" ]] || die "title is required"

  cd "$ROOT_DIR"
  mkdir -p chapters/scene_cards chapters/drafts chapters/final chapters/records

  local n label
  n="$(chapter_num "$number")"
  label="$(chapter_label "$number")"

  write_if_missing "chapters/scene_cards/${label}_${title}_章节卡.md" "# ${label} ${title} 章节卡

## 前文连续性承接

- 必须先读取：progress/continuity_index.md
- 必须先读取：progress/chapter_summary.md
- 必须先确认：前一章结尾、人物状态、能力阶段、未回收伏笔

## 本章任务

待填写。

## 上章承接

待填写。

## 本章必须出现

待填写。

## 本章禁止出现

- 不得改写前文事实。
- 不得提前解决长期主线。
- 不得新增未登记核心设定。

## 不可改写的前文事实

待填写。

## 场景列表

待填写。

## 人物变化

待填写。

## 主线推进

待填写。

## 章末钩子

待填写。

## 需要更新的记录

- progress/current_context.md
- progress/continuity_index.md
- progress/active_threads.md
- progress/timeline.md
- progress/word_count.md
- progress/publishing_log.md"

  write_if_missing "chapters/drafts/${label}_${title}_草稿.md" "# ${label} ${title} 草稿

> 状态：未生成正文。
> 生成前必须确认对应章节卡已完成，并通过连续性检查。

## 草稿正文

待生成。"

  write_if_missing "chapters/records/${label}_${title}_审稿记录.md" "# ${label} ${title} 审稿记录

## 结论

待审稿。

## 必须修改

待填写。

## 建议修改

待填写。

## 连续性风险

待填写。

## 是否可进入定稿

否。"

  write_if_missing "chapters/records/${label}_${title}_连续性检查.md" "# ${label} ${title} 连续性检查

## 结论

待检查。

## 是否破坏第1-30章连续性

待检查。

## 冲突列表

待填写。

## 风险等级

待填写。

## 需要修复的文件

待填写。

## 是否允许规划下一章

否。"

  printf '\nCreated workflow skeleton for %s %s.\n' "$label" "$title"
}

context_pack() {
  local number="$1"
  cd "$ROOT_DIR"

  local n label file
  n="$(chapter_num "$number")"
  label="$(chapter_label "$number")"
  file="chapters/records/${label}_上下文包.md"

  if [[ -e "$file" ]]; then
    die "context packet already exists: $file"
  fi

  {
    printf '# %s 上下文包\n\n' "$label"
    printf '## 使用方式\n\n'
    printf '把本文件作为生成章节卡前的索引。不要直接把它当正文。\n\n'
    printf '## 必读顺序\n\n'
    printf '1. README.md\n'
    printf '2. progress/current_context.md\n'
    printf '3. progress/continuity_index.md\n'
    printf '4. progress/chapter_summary.md\n'
    printf '5. progress/active_threads.md\n'
    printf '6. progress/timeline.md\n'
    printf '7. outlines/chapter_queue.md\n'
    printf '8. prompts/01_generate_scene_card.md\n\n'
    printf '## 连续性硬约束\n\n'
    printf '- 不得改写第1-30章已经发生的事件。\n'
    printf '- 不得无证据推翻人物关系、能力阶段、数值变化。\n'
    printf '- 无法确认前一章结尾时，禁止生成章节卡。\n\n'
    printf '## 当前上下文摘要来源\n\n'
    printf '- progress/current_context.md\n'
    printf '- progress/continuity_index.md\n'
    printf '- progress/chapter_summary.md\n'
  } > "$file"

  printf 'CREATE %s\n' "$file"
}

main() {
  ensure_repo
  local cmd="${1:-}"
  case "$cmd" in
    check)
      check_system
      ;;
    status)
      status_system
      ;;
    new-chapter)
      [[ $# -ge 3 ]] || die "usage: scripts/novelctl.sh new-chapter <number> <title>"
      new_chapter "$2" "$3"
      ;;
    context-pack)
      [[ $# -eq 2 ]] || die "usage: scripts/novelctl.sh context-pack <number>"
      context_pack "$2"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      usage
      die "unknown command: $cmd"
      ;;
  esac
}

main "$@"
