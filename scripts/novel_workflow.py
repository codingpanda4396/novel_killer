#!/usr/bin/env python3
"""
novel0 unified production workflow.

This script manages the repo workflow and can call an OpenAI-compatible
Chat Completions API. It does not require third-party Python packages.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "bible",
    "chapters",
    "chapters/scene_cards",
    "chapters/drafts",
    "chapters/final",
    "chapters/records",
    "outlines",
    "progress",
    "prompts",
]

REQUIRED_FILES = [
    "README.md",
    "bible/00_story_bible.md",
    "bible/01_characters.md",
    "bible/02_power_system.md",
    "bible/03_style_guide.md",
    "bible/04_forbidden_rules.md",
    "outlines/00_full_outline.md",
    "outlines/01_volume_outline.md",
    "outlines/02_cold_start_0_80k.md",
    "outlines/chapter_queue.md",
    "progress/active_threads.md",
    "progress/chapter_summary.md",
    "progress/continuity_index.md",
    "progress/current_context.md",
    "progress/timeline.md",
    "progress/word_count.md",
    "progress/publishing_log.md",
    "prompts/00_build_current_context.md",
    "prompts/01_generate_scene_card.md",
    "prompts/02_generate_chapter_draft.md",
    "prompts/03_review_chapter.md",
    "prompts/04_rewrite_chapter.md",
    "prompts/05_update_record.md",
    "prompts/06_continuity_check.md",
    "prompts/07_next_chapter_planner.md",
]

STAGE_PROMPTS = {
    "build_context": "prompts/00_build_current_context.md",
    "scene_card": "prompts/01_generate_scene_card.md",
    "draft": "prompts/02_generate_chapter_draft.md",
    "review": "prompts/03_review_chapter.md",
    "rewrite": "prompts/04_rewrite_chapter.md",
    "update_record": "prompts/05_update_record.md",
    "continuity_check": "prompts/06_continuity_check.md",
    "next_planner": "prompts/07_next_chapter_planner.md",
    "batch_planner": "prompts/08_batch_planner.md",
}

MULTI_FILE_STAGES = {"update_record", "next_planner", "batch_planner"}


@dataclass(frozen=True)
class ChapterFiles:
    number: int
    title: str
    label: str
    scene_card: Path
    draft: Path
    review: Path
    continuity: Path
    final: Path
    context_pack: Path
    update_record: Path


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        print(f"SKIP exists {rel(path)}")
        return
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print(f"WRITE {rel(path)}")


def chapter_label(number: int) -> str:
    return f"第{number:03d}章"


def chapter_files(number: int, title: str | None = None) -> ChapterFiles:
    label = chapter_label(number)
    title = title or find_title_for_chapter(label) or "未命名"
    stem = f"{label}_{title}"
    return ChapterFiles(
        number=number,
        title=title,
        label=label,
        scene_card=ROOT / "chapters" / "scene_cards" / f"{stem}_章节卡.md",
        draft=ROOT / "chapters" / "drafts" / f"{stem}_草稿.md",
        review=ROOT / "chapters" / "records" / f"{stem}_审稿记录.md",
        continuity=ROOT / "chapters" / "records" / f"{stem}_连续性检查.md",
        final=ROOT / "chapters" / "final" / f"{stem}.md",
        context_pack=ROOT / "chapters" / "records" / f"{label}_上下文包.md",
        update_record=ROOT / "chapters" / "records" / f"{stem}_记录更新建议.md",
    )


def find_title_for_chapter(label: str) -> str | None:
    for folder in ["chapters/scene_cards", "chapters/drafts", "chapters/final", "chapters/records"]:
        for path in (ROOT / folder).glob(f"{label}_*.md"):
            name = path.stem
            for suffix in ["_章节卡", "_草稿", "_审稿记录", "_连续性检查", "_记录更新建议"]:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
            return name.replace(f"{label}_", "", 1)
    return None


def check_system() -> int:
    failed = 0
    for item in REQUIRED_DIRS:
        path = ROOT / item
        if path.is_dir():
            print(f"OK dir  {item}")
        else:
            print(f"MISS dir {item}")
            failed = 1
    for item in REQUIRED_FILES:
        path = ROOT / item
        if path.is_file() and path.stat().st_size > 0:
            print(f"OK file {item}")
        else:
            print(f"MISS file {item}")
            failed = 1
    return failed


def count_md(folder: str, recursive: bool = False) -> int:
    base = ROOT / folder
    pattern = "**/*.md" if recursive else "*.md"
    return sum(1 for _ in base.glob(pattern))


def git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def status() -> None:
    print("# novel0 status\n")
    print(f"Branch: {git_branch()}")
    print(f"Historical chapter files: {count_md('chapters')}")
    print(f"Scene cards: {count_md('chapters/scene_cards')}")
    print(f"Drafts: {count_md('chapters/drafts')}")
    print(f"Final chapters: {count_md('chapters/final')}")
    print("\nNext required step:")
    print("- Run build-context before producing any new chapter.")
    print("- If current_context blocks production, fix outlines/progress first.")


def init_config(force: bool = False) -> None:
    source = ROOT / "config" / "workflow.example.json"
    target = ROOT / "config" / "workflow.local.json"
    if target.exists() and not force:
        print(f"SKIP exists {rel(target)}")
        return
    shutil.copyfile(source, target)
    print(f"CREATE {rel(target)}")
    print("Edit this file and set provider.base_url, provider.api_key_env, and stage models.")


def scaffold_chapter(number: int, title: str) -> ChapterFiles:
    files = chapter_files(number, title)
    write_text(
        files.scene_card,
        f"""# {files.label} {title} 章节卡

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
- progress/publishing_log.md
""",
        overwrite=False,
    )
    write_text(
        files.draft,
        f"""# {files.label} {title} 草稿

> 状态：未生成正文。
> 生成前必须确认对应章节卡已完成，并通过连续性检查。

## 草稿正文

待生成。
""",
        overwrite=False,
    )
    write_text(
        files.review,
        f"""# {files.label} {title} 审稿记录

## 结论

待审稿。

## 必须修改

待填写。

## 建议修改

待填写。

## 连续性风险

待填写。

## 是否可进入定稿

否。
""",
        overwrite=False,
    )
    write_text(
        files.continuity,
        f"""# {files.label} {title} 连续性检查

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

否。
""",
        overwrite=False,
    )
    return files


def context_pack(number: int, title: str | None = None) -> Path:
    files = chapter_files(number, title)
    content = f"""# {files.label} 上下文包

## 使用方式

把本文件作为生成章节卡前的索引。不要直接把它当正文。

## 必读顺序

1. README.md
2. progress/current_context.md
3. progress/continuity_index.md
4. progress/chapter_summary.md
5. progress/active_threads.md
6. progress/timeline.md
7. outlines/chapter_queue.md
8. prompts/01_generate_scene_card.md

## 连续性硬约束

- 不得改写第1-30章已经发生的事件。
- 不得无证据推翻人物关系、能力阶段、数值变化。
- 无法确认前一章结尾时，禁止生成章节卡。

## 当前上下文摘要来源

- progress/current_context.md
- progress/continuity_index.md
- progress/chapter_summary.md
"""
    write_text(files.context_pack, content, overwrite=False)
    return files.context_pack


def load_config(path: Path | None) -> dict[str, Any]:
    config_path = path or ROOT / "config" / "workflow.local.json"
    if not config_path.exists():
        die(f"missing config: {rel(config_path)}; run `python3 scripts/novel_workflow.py init-config`")
    return json.loads(read_text(config_path))


def stage_settings(config: dict[str, Any], stage: str) -> dict[str, Any]:
    defaults = config.get("defaults", {})
    settings = dict(defaults)
    settings.update(config.get("stages", {}).get(stage, {}))
    if "model" not in settings:
        die(f"missing model for stage: {stage}")
    return settings


def provider_settings(config: dict[str, Any]) -> dict[str, Any]:
    provider = config.get("provider", {})
    if provider.get("type") != "openai_compatible":
        die("only provider.type=openai_compatible is supported")
    if not provider.get("base_url"):
        die("missing provider.base_url")
    if not provider.get("api_key_env"):
        die("missing provider.api_key_env")
    return provider


def gather_files(paths: list[str]) -> str:
    chunks: list[str] = []
    for item in paths:
        path = ROOT / item
        if path.is_file():
            chunks.append(f"\n\n--- FILE: {item} ---\n{read_text(path)}")
    return "".join(chunks)


def find_existing_chapter_file(folder: str, number: int, title: str | None = None) -> Path | None:
    files = chapter_files(number, title)
    candidates = {
        "scene_card": files.scene_card,
        "draft": files.draft,
        "review": files.review,
        "continuity": files.continuity,
        "final": files.final,
    }
    direct = candidates.get(folder)
    if direct and direct.exists():
        return direct
    label = chapter_label(number)
    search_dir = {
        "scene_card": ROOT / "chapters" / "scene_cards",
        "draft": ROOT / "chapters" / "drafts",
        "review": ROOT / "chapters" / "records",
        "continuity": ROOT / "chapters" / "records",
        "final": ROOT / "chapters" / "final",
    }.get(folder)
    if not search_dir:
        return None
    suffix = {
        "scene_card": "_章节卡.md",
        "draft": "_草稿.md",
        "review": "_审稿记录.md",
        "continuity": "_连续性检查.md",
        "final": ".md",
    }[folder]
    matches = sorted(search_dir.glob(f"{label}_*{suffix}"))
    return matches[0] if matches else None


def stage_inputs(stage: str, number: int | None, title: str | None) -> list[str]:
    common = [
        "README.md",
        "progress/current_context.md",
        "progress/continuity_index.md",
        "progress/chapter_summary.md",
        "progress/active_threads.md",
        "progress/timeline.md",
        "outlines/chapter_queue.md",
        "bible/00_story_bible.md",
        "bible/01_characters.md",
        "bible/02_power_system.md",
        "bible/03_style_guide.md",
        "bible/04_forbidden_rules.md",
    ]
    if number is None:
        return common

    extra: list[str] = []
    for key in ["scene_card", "draft", "review", "continuity", "final"]:
        found = find_existing_chapter_file(key, number, title)
        if found:
            extra.append(rel(found))
    if stage in {"draft", "review", "rewrite", "continuity_check", "update_record"}:
        previous = sorted((ROOT / "chapters").glob("*.md"))[-3:]
        extra.extend(rel(path) for path in previous)
    return common + extra


def output_path_for_stage(stage: str, number: int | None, title: str | None) -> Path | None:
    if stage == "build_context":
        return ROOT / "progress" / "current_context.md"
    if number is None:
        return None
    files = chapter_files(number, title)
    return {
        "scene_card": files.scene_card,
        "draft": files.draft,
        "review": files.review,
        "rewrite": files.draft,
        "continuity_check": files.continuity,
        "update_record": files.update_record,
        "next_planner": ROOT / "outlines" / "chapter_queue.md",
    }.get(stage)


def build_messages(stage: str, number: int | None, title: str | None, output_path: Path | None) -> list[dict[str, str]]:
    prompt_file = ROOT / STAGE_PROMPTS[stage]
    paths = [STAGE_PROMPTS[stage]] + stage_inputs(stage, number, title)
    file_context = gather_files(paths)

    if stage in MULTI_FILE_STAGES:
        output_rule = textwrap.dedent(
            """
            输出必须是严格 JSON，不要 Markdown 代码块。格式：
            {
              "files": {
                "relative/path.md": "完整文件内容"
              },
              "notes": ["简短说明"]
            }
            只允许写入 progress/、outlines/chapter_queue.md 或 chapters/records/ 下的文件。
            """
        ).strip()
    else:
        target = rel(output_path) if output_path else "stdout"
        output_rule = f"只输出目标文件 `{target}` 的完整 Markdown 内容，不要解释，不要代码块。"

    task = textwrap.dedent(
        f"""
        你正在操作 novel0 小说生产系统。

        当前阶段：{stage}
        目标章号：{number if number is not None else "无"}
        章节标题：{title or "无"}

        硬性要求：
        - 不得改写已有章节事实。
        - 不得跳过连续性保护。
        - 不得生成本阶段以外的文件内容。
        - 如果信息不足，必须在输出中标注阻塞原因。

        输出规则：
        {output_rule}

        以下是本阶段 prompt 和相关上下文：
        {file_context}
        """
    ).strip()

    return [
        {"role": "system", "content": "你是严格遵守仓库流程的长篇小说生产系统执行器。"},
        {"role": "user", "content": task},
    ]


def call_openai_compatible(config: dict[str, Any], stage: str, messages: list[dict[str, str]]) -> str:
    provider = provider_settings(config)
    settings = stage_settings(config, stage)
    api_key = os.environ.get(provider["api_key_env"])
    if not api_key:
        die(f"environment variable not set: {provider['api_key_env']}")

    base_url = provider["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": settings["model"],
        "messages": messages,
        "temperature": settings.get("temperature", 0.7),
        "max_tokens": settings.get("max_tokens", 6000),
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        die(f"API HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        die(f"API request failed: {exc}")

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        die(f"unexpected API response: {exc}; body={body}")


def strip_fences(text: str) -> str:
    match = re.fullmatch(r"\s*```(?:json|markdown|md)?\s*(.*?)\s*```\s*", text, flags=re.S)
    return match.group(1) if match else text


def safe_write_model_files(raw: str, dry_run: bool) -> None:
    content = strip_fences(raw).strip()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        die(f"model did not return valid JSON for multi-file stage: {exc}")
    files = payload.get("files")
    if not isinstance(files, dict):
        die("multi-file stage JSON must contain object field: files")
    allowed_prefixes = ("progress/", "chapters/records/")
    allowed_exact = {"outlines/chapter_queue.md"}
    for name, file_content in files.items():
        if not isinstance(name, str) or not isinstance(file_content, str):
            die("files entries must be string path to string content")
        clean = Path(name)
        if clean.is_absolute() or ".." in clean.parts:
            die(f"unsafe output path: {name}")
        allowed = name in allowed_exact or any(name.startswith(prefix) for prefix in allowed_prefixes)
        if not allowed:
            die(f"output path not allowed for multi-file stage: {name}")
        target = ROOT / clean
        if dry_run:
            print(f"DRY would write {name} ({len(file_content)} chars)")
        else:
            write_text(target, file_content)
    for note in payload.get("notes", []):
        print(f"NOTE {note}")


def run_stage(args: argparse.Namespace) -> None:
    stage = args.stage
    if stage not in STAGE_PROMPTS:
        die(f"unknown stage: {stage}")
    title = args.title or find_title_for_chapter(chapter_label(args.number)) if args.number else args.title
    output_path = output_path_for_stage(stage, args.number, title)
    messages = build_messages(stage, args.number, title, output_path)
    if args.print_prompt:
        print(messages[-1]["content"])
        return
    config = load_config(args.config)
    
    # 如果是 dry-run 模式，跳过 API 调用
    if args.dry_run:
        if stage in MULTI_FILE_STAGES:
            print(f"DRY would write multi-file stage {stage}")
        elif output_path:
            print(f"DRY would write {rel(output_path)}")
        else:
            print(f"DRY would print {stage} output")
        return
    
    raw = call_openai_compatible(config, stage, messages)
    if stage in MULTI_FILE_STAGES:
        safe_write_model_files(raw, args.dry_run)
        return
    if output_path is None:
        print(raw)
    elif args.dry_run:
        print(f"DRY would write {rel(output_path)} ({len(raw)} chars)")
        print(strip_fences(raw))
    else:
        write_text(output_path, strip_fences(raw))


def run_full(args: argparse.Namespace) -> None:
    if not args.title:
        die("--title is required for run-full")
    scaffold_chapter(args.number, args.title)
    context_pack(args.number, args.title)
    stages = [
        "build_context",
        "scene_card",
        "draft",
        "review",
        "continuity_check",
        "update_record",
        "next_planner",
    ]
    for stage in stages:
        print(f"\n== Stage: {stage} ==")
        stage_args = argparse.Namespace(
            stage=stage,
            number=args.number,
            title=args.title,
            config=args.config,
            dry_run=args.dry_run,
            print_prompt=False,
        )
        run_stage(stage_args)


def generate_chapter_title(number: int) -> str:
    """生成章节标题（基于章节号和上下文）"""
    # 从 chapter_queue.md 中查找对应章节的标题
    queue_path = ROOT / "outlines" / "chapter_queue.md"
    if queue_path.exists():
        content = read_text(queue_path)
        # 查找格式：| 31 | 标题 | ...
        pattern = rf"\|\s*{number}\s*\|\s*([^|]+)\s*\|"
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
    
    # 如果找不到，返回默认标题
    return f"第{number}章"


def save_batch_progress(progress_file: Path, chapter_num: int, status: str = "completed") -> None:
    """保存批量生成进度到JSON文件"""
    progress = {}
    if progress_file.exists():
        try:
            progress = json.loads(read_text(progress_file))
        except json.JSONDecodeError:
            progress = {}
    
    if "chapters" not in progress:
        progress["chapters"] = {}
    
    progress["chapters"][str(chapter_num)] = {
        "status": status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    progress["last_chapter"] = chapter_num
    progress["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    write_text(progress_file, json.dumps(progress, ensure_ascii=False, indent=2))


def load_batch_progress(progress_file: Path) -> dict:
    """加载批量生成进度"""
    if not progress_file.exists():
        return {"chapters": {}, "last_chapter": 0}
    try:
        return json.loads(read_text(progress_file))
    except json.JSONDecodeError:
        return {"chapters": {}, "last_chapter": 0}


def run_full_chapter(number: int, title: str, config: Path | None, dry_run: bool = False, check_quality: bool = False) -> bool:
    """运行单章完整流程，返回是否成功"""
    try:
        # 构造 run-full 参数
        args = argparse.Namespace(
            number=number,
            title=title,
            config=config,
            dry_run=dry_run,
        )
        run_full(args)
        
        # 如果启用质量检查，运行额外的审稿阶段
        if check_quality and not dry_run:
            print(f"\n== Quality Check for Chapter {number} ==")
            # 运行额外的连续性检查
            check_args = argparse.Namespace(
                stage="continuity_check",
                number=number,
                title=title,
                config=config,
                dry_run=False,
                print_prompt=False,
            )
            run_stage(check_args)
        
        return True
    except Exception as e:
        print(f"ERROR generating chapter {number}: {e}")
        return False


def run_batch(args: argparse.Namespace) -> None:
    """批量生成章节"""
    start = args.start
    count = args.count
    check_quality = args.check
    resume = args.resume
    config = args.config
    dry_run = args.dry_run
    
    # 检查断点续传
    progress_file = ROOT / "progress" / "batch_progress.json"
    if resume:
        progress = load_batch_progress(progress_file)
        last_chapter = progress.get("last_chapter", 0)
        if last_chapter >= start:
            start = last_chapter + 1
            print(f"Resuming from chapter {start} (last completed: {last_chapter})")
    
    print(f"\n{'='*60}")
    print(f"开始批量生成")
    print(f"起始章节: {start}")
    print(f"生成数量: {count}")
    print(f"质量检查: {'启用' if check_quality else '禁用'}")
    print(f"断点续传: {'启用' if resume else '禁用'}")
    print(f"{'='*60}\n")
    
    success_count = 0
    failed_chapters = []
    
    for i in range(count):
        chapter_num = start + i
        
        # 生成章节标题
        title = generate_chapter_title(chapter_num)
        
        print(f"\n{'='*60}")
        print(f"[{i+1}/{count}] 开始生成第 {chapter_num} 章: {title}")
        print(f"{'='*60}")
        
        # 执行完整流程
        success = run_full_chapter(chapter_num, title, config, dry_run, check_quality)
        
        if success:
            success_count += 1
            save_batch_progress(progress_file, chapter_num, "completed")
            print(f"\n✓ 第 {chapter_num} 章生成完成")
        else:
            failed_chapters.append(chapter_num)
            save_batch_progress(progress_file, chapter_num, "failed")
            print(f"\n✗ 第 {chapter_num} 章生成失败")
            
            # 如果失败，询问是否继续
            if not dry_run and i < count - 1:
                print(f"\n是否继续生成下一章？(y/n)")
                # 在自动化模式下默认继续
                continue
        
        # 生成间隔（避免API限流）
        if i < count - 1 and not dry_run:
            print(f"\n等待2秒后继续...")
            time.sleep(2)
    
    # 打印总结
    print(f"\n{'='*60}")
    print(f"批量生成完成")
    print(f"成功: {success_count}/{count}")
    if failed_chapters:
        print(f"失败章节: {', '.join(map(str, failed_chapters))}")
    print(f"{'='*60}")
    
    # 保存最终进度
    if not dry_run:
        save_batch_progress(progress_file, start + count - 1, "batch_completed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="novel0 unified production workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check")
    sub.add_parser("status")
    init = sub.add_parser("init-config")
    init.add_argument("--force", action="store_true")

    new = sub.add_parser("new-chapter")
    new.add_argument("number", type=int)
    new.add_argument("title")

    pack = sub.add_parser("context-pack")
    pack.add_argument("number", type=int)
    pack.add_argument("--title")

    stage = sub.add_parser("run-stage")
    stage.add_argument("stage", choices=sorted(STAGE_PROMPTS))
    stage.add_argument("--number", type=int)
    stage.add_argument("--title")
    stage.add_argument("--config", type=Path)
    stage.add_argument("--dry-run", action="store_true")
    stage.add_argument("--print-prompt", action="store_true")

    full = sub.add_parser("run-full")
    full.add_argument("--number", type=int, required=True)
    full.add_argument("--title", required=True)
    full.add_argument("--config", type=Path)
    full.add_argument("--dry-run", action="store_true")

    batch = sub.add_parser("run-batch")
    batch.add_argument("--start", type=int, required=True, help="起始章节号")
    batch.add_argument("--count", type=int, required=True, help="生成章节数量")
    batch.add_argument("--check", action="store_true", help="启用质量检查")
    batch.add_argument("--resume", action="store_true", help="断点续传")
    batch.add_argument("--config", type=Path)
    batch.add_argument("--dry-run", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    os.chdir(ROOT)

    if args.command == "check":
        raise SystemExit(check_system())
    if args.command == "status":
        status()
        return
    if args.command == "init-config":
        init_config(args.force)
        return
    if args.command == "new-chapter":
        scaffold_chapter(args.number, args.title)
        return
    if args.command == "context-pack":
        context_pack(args.number, args.title)
        return
    if args.command == "run-stage":
        run_stage(args)
        return
    if args.command == "run-full":
        run_full(args)
        return
    if args.command == "run-batch":
        run_batch(args)
        return
    parser.print_help()


if __name__ == "__main__":
    main()
