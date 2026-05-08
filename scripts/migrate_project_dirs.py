#!/usr/bin/env python3
"""One-time migration script: restructure project directories from old layout to new layout.

Old layout:
  bible/, outlines/, state/, corpus/, generation/, reviews/, publish/, intelligence/, experiments/

New layout:
  market/        ← intelligence/
  story/bible    ← bible/
  story/outlines ← outlines/
  story/state    ← state/
  production/generation ← generation/
  production/reviews    ← reviews/
  production/corpus     ← corpus/
  production/publish    ← publish/
  production/experiments ← experiments/

Usage:
  python scripts/migrate_project_dirs.py --project life_balance [--dry-run] [--no-backup] [--force]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Repo root
ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"

# Old dir → new dir mappings (relative to project root)
_MOVES: list[tuple[str, str]] = [
    ("intelligence", "market"),
    ("bible", "story/bible"),
    ("outlines", "story/outlines"),
    ("state", "story/state"),
    ("generation", "production/generation"),
    ("reviews", "production/reviews"),
    ("corpus", "production/corpus"),
    ("publish", "production/publish"),
    ("experiments", "production/experiments"),
]


def _run_git(args: list[str], cwd: Path = ROOT) -> int:
    """Run a git command, return exit code."""
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  git {' '.join(args)}: {result.stderr.strip()}", file=sys.stderr)
    return result.returncode


def migrate_project(project_id: str, dry_run: bool = False, no_backup: bool = False, force: bool = False) -> None:
    project_path = PROJECTS_DIR / project_id
    if not project_path.is_dir():
        print(f"ERROR: Project not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    if not (project_path / "project.json").is_file():
        print(f"ERROR: No project.json in {project_path}", file=sys.stderr)
        sys.exit(1)

    # Check for dirty tree (unless --force)
    if not force and not dry_run:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
        if result.stdout.strip():
            print("ERROR: Git working tree is dirty. Use --force to proceed anyway.", file=sys.stderr)
            sys.exit(1)

    # Backup
    if not no_backup and not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_path = PROJECTS_DIR / f"{project_id}.bak-{timestamp}"
        if backup_path.exists():
            print(f"Backup already exists: {backup_path}, skipping backup.")
        else:
            print(f"Backing up: {project_path} → {backup_path}")
            shutil.copytree(project_path, backup_path)

    # Check which moves are needed
    moves_needed: list[tuple[str, str]] = []
    for old_name, new_name in _MOVES:
        old_path = project_path / old_name
        new_path = project_path / new_name
        if old_path.is_dir() and not new_path.exists():
            moves_needed.append((old_name, new_name))
        elif old_path.is_dir() and new_path.exists():
            print(f"  SKIP: both {old_name} and {new_name} exist")
        elif not old_path.is_dir():
            print(f"  SKIP: {old_name} does not exist")

    if not moves_needed:
        print("Nothing to migrate.")
    else:
        print(f"\n{'DRY RUN: ' if dry_run else ''}Migrating {len(moves_needed)} directories:")
        for old_name, new_name in moves_needed:
            print(f"  {old_name} → {new_name}")
            if not dry_run:
                # Create parent dirs
                (project_path / new_name).parent.mkdir(parents=True, exist_ok=True)
                # git mv
                rc = _run_git(["mv", str(project_path / old_name), str(project_path / new_name)])
                if rc != 0:
                    print(f"  ERROR: git mv failed for {old_name}", file=sys.stderr)
                    sys.exit(1)

    # Update project.json directories mapping
    cfg_path = project_path / "project.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    old_dirs = dict(cfg.get("directories", {}))
    cfg["directories"] = {
        "intelligence": "market",
        "bible": "story/bible",
        "outlines": "story/outlines",
        "state": "story/state",
        "generation": "production/generation",
        "reviews": "production/reviews",
        "corpus": "production/corpus",
        "publish": "production/publish",
        "experiments": "production/experiments",
    }
    if not dry_run:
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nUpdated {cfg_path}")
    else:
        print(f"\nWould update {cfg_path}:")
        print(f"  old: {json.dumps(old_dirs, ensure_ascii=False)}")
        print(f"  new: {json.dumps(cfg['directories'], ensure_ascii=False)}")

    print(f"\n{'DRY RUN ' if dry_run else ''}Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate project directories to new layout")
    parser.add_argument("--project", required=True, help="Project ID to migrate")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup before migration")
    parser.add_argument("--force", action="store_true", help="Allow running on dirty git tree")
    args = parser.parse_args()
    migrate_project(args.project, dry_run=args.dry_run, no_backup=args.no_backup, force=args.force)


if __name__ == "__main__":
    main()
