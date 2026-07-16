#!/usr/bin/env python3
"""Publish selected AI news stories into OpenVibeAI-data.

This script replaces the AI News Data Publisher workflow's inline publisher with
an independently testable command. Default mode is a dry run. Use --write to
modify files and --commit to also create a git commit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

DATA_BASE = Path("data/ai-news")
LATEST_FILE = DATA_BASE / "latest.json"
ARCHIVE_DIR = DATA_BASE / "archive"
STORY_LIST_KEYS = ("stories", "items", "news", "articles")
REQUIRED_PAYLOAD_KEYS = {"selected_ids", "selected_count", "stories"}
REQUIRED_STORY_KEYS = {
    "id",
    "title",
    "slug",
    "summary",
    "sourceUrl",
    "publishedAt",
    "category",
    "tags",
}


def emit(result: dict[str, Any]) -> None:
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def stop(status: str, reason: str, **extra: Any) -> None:
    emit({"status": status, "reason": reason, **extra})
    raise SystemExit(0)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise
    except Exception as exc:
        stop("blocked", "json_read_failed", path=str(path), error=str(exc))


def extract_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in STORY_LIST_KEYS:
            items = value.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
    return []


def load_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return extract_items(read_json(path))


def parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def story_key(story: dict[str, Any]) -> str:
    return (
        str(story.get("sourceUrl") or "").strip().lower()
        or str(story.get("slug") or "").strip().lower()
        or str(story.get("id") or "").strip().lower()
    )


def output_month_path(story: dict[str, Any], fallback: dt.date) -> Path:
    date_value = parse_date(story.get("publishedAt") or story.get("createdAt")) or fallback
    return ARCHIVE_DIR / f"{date_value.year:04d}-{date_value.month:02d}.json"


def write_json_atomic(path: Path, value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return True


def read_payload(payload_file: str | None) -> dict[str, Any]:
    try:
        if payload_file:
            payload = json.loads(Path(payload_file).read_text())
        else:
            if sys.stdin.isatty():
                stop("blocked", "missing_payload", detail="Pass --payload-file or pipe JSON on stdin.")
            payload = json.load(sys.stdin)
    except Exception as exc:
        stop("blocked", "payload_parse_failed", error=str(exc))
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception as exc:
            stop("blocked", "payload_json_string_parse_failed", error=str(exc))
    if not isinstance(payload, dict):
        stop("blocked", "payload_must_be_object")
    return payload


def validate_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    missing = sorted(REQUIRED_PAYLOAD_KEYS - set(payload))
    if missing:
        stop("blocked", "payload_missing_required_keys", missing=missing)
    stories = payload.get("stories")
    if not isinstance(stories, list):
        stop("blocked", "stories_must_be_array")
    publishable: list[dict[str, Any]] = []
    for index, story in enumerate(stories):
        if not isinstance(story, dict):
            stop("blocked", "story_must_be_object", index=index)
        if story.get("publishable") is False:
            continue
        story_missing = sorted(REQUIRED_STORY_KEYS - set(story))
        if story_missing:
            stop("blocked", "story_missing_required_keys", index=index, missing=story_missing)
        publishable.append(story)
    for order, story in enumerate(publishable, start=1):
        story["order"] = order
        story["featured"] = order == 1
    return publishable


def build_plan(repo: Path, payload: dict[str, Any], today: dt.date) -> dict[str, Any]:
    selected = validate_payload(payload)
    latest_path = repo / LATEST_FILE
    cutoff = today - dt.timedelta(days=7)

    merged: dict[str, dict[str, Any]] = {}
    for item in load_items(latest_path):
        key = story_key(item)
        if key:
            merged[key] = item
    for item in selected:
        key = story_key(item)
        if key:
            merged[key] = item

    latest_items: list[dict[str, Any]] = []
    archived_items: list[dict[str, Any]] = []
    for item in merged.values():
        item_date = parse_date(item.get("publishedAt") or item.get("createdAt"))
        if item_date and item_date < cutoff:
            archived_items.append(item)
        else:
            latest_items.append(item)

    desired: dict[Path, dict[str, Any]] = {
        LATEST_FILE: {"updatedAt": today.isoformat(), "stories": latest_items}
    }

    archive_groups: dict[Path, list[dict[str, Any]]] = {}
    for item in archived_items:
        archive_groups.setdefault(output_month_path(item, today), []).append(item)

    for relative_path, items in archive_groups.items():
        archive_map: dict[str, dict[str, Any]] = {}
        for existing in load_items(repo / relative_path):
            key = story_key(existing)
            if key:
                archive_map[key] = existing
        for item in items:
            key = story_key(item)
            if key:
                archive_map[key] = item
        sorted_items = sorted(
            archive_map.values(),
            key=lambda story: str(story.get("publishedAt") or story.get("createdAt") or ""),
            reverse=True,
        )
        desired[relative_path] = {"updatedAt": today.isoformat(), "stories": sorted_items}

    planned_writes: list[dict[str, Any]] = []
    changed_paths: list[str] = []
    for relative_path, value in sorted(desired.items(), key=lambda pair: str(pair[0])):
        absolute_path = repo / relative_path
        next_text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        previous_text = absolute_path.read_text() if absolute_path.exists() else None
        changed = previous_text != next_text
        if changed:
            changed_paths.append(str(relative_path))
        planned_writes.append({"path": str(relative_path), "changed": changed, "story_count": len(extract_items(value))})

    return {
        "payload_selected_ids": [str(story.get("id") or "") for story in selected],
        "selected_count": len(selected),
        "latest_count": len(latest_items),
        "archived_count": len(archived_items),
        "planned_writes": planned_writes,
        "changed_paths": changed_paths,
        "desired": desired,
    }


def validate_existing_data(repo: Path) -> dict[str, Any]:
    paths = [repo / LATEST_FILE, repo / DATA_BASE / "archive.json"]
    archive_dir = repo / ARCHIVE_DIR
    if archive_dir.exists():
        paths.extend(sorted(archive_dir.glob("*.json")))
    files: list[dict[str, Any]] = []
    all_valid = True
    for path in paths:
        if not path.exists():
            files.append({"path": str(path.relative_to(repo)), "exists": False, "valid": None})
            continue
        try:
            json.loads(path.read_text())
            valid = True
        except Exception:
            valid = False
        all_valid = all_valid and valid
        files.append({"path": str(path.relative_to(repo)), "exists": True, "valid": valid})
    return {"status": "ok" if all_valid else "blocked", "files": files}


def git_status(repo: Path) -> list[str]:
    try:
        output = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(repo), text=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        stop("blocked", "git_status_failed", error=(exc.stderr or str(exc)).strip())
    return [line for line in output.splitlines() if line]


def unrelated_git_changes(repo: Path, allowed_paths: set[str]) -> list[str]:
    unsafe: list[str] = []
    for line in git_status(repo):
        path_text = line[3:].strip() if len(line) > 3 else line.strip()
        if path_text not in allowed_paths and not path_text.startswith("data/ai-news/"):
            unsafe.append(line)
    return unsafe


def commit_paths(repo: Path, paths: list[str], today: dt.date) -> str:
    subprocess.check_call(["git", "add", "--", *paths], cwd=str(repo))
    subprocess.check_call(["git", "commit", "-m", f"Update AI news data {today.isoformat()}"], cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo), text=True).strip()


def run_publish(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        stop("blocked", "repo_not_found", repo=str(repo))
    try:
        today = dt.date.fromisoformat(args.date[:10])
    except ValueError:
        stop("blocked", "invalid_date", date=args.date)

    if args.validate:
        return validate_existing_data(repo)

    payload = read_payload(args.payload_file)
    plan = build_plan(repo, payload, today)
    base_result = {
        "selected_count": plan["selected_count"],
        "selected_ids": plan["payload_selected_ids"],
        "written_paths": [],
        "planned_writes": plan["planned_writes"],
        "commit_hash": None,
        "latest_count": plan["latest_count"],
        "archived_count": plan["archived_count"],
        "target_repo": str(repo),
        "target_data_path": str(DATA_BASE),
    }

    if args.dry_run or not args.write:
        return {"status": "dry_run", **base_result}

    changed_paths: list[str] = []
    for relative_path, value in plan["desired"].items():
        if write_json_atomic(repo / relative_path, value):
            changed_paths.append(str(relative_path))
        json.loads((repo / relative_path).read_text())

    base_result["written_paths"] = changed_paths
    if not changed_paths:
        return {"status": "no_change", **base_result}
    if not args.commit:
        return {"status": "written", **base_result}

    unsafe = unrelated_git_changes(repo, set(changed_paths))
    if unsafe:
        return {"status": "blocked", "reason": "unrelated_git_changes_present", "unsafe": unsafe, **base_result}

    commit_hash = commit_paths(repo, changed_paths, today)
    return {"status": "committed", **base_result, "commit_hash": commit_hash}


def parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description="Publish selected AI news data.")
    arg_parser.add_argument("--payload-file", help="JSON payload file. If omitted, reads stdin.")
    arg_parser.add_argument("--date", default=dt.date.today().isoformat(), help="YYYY-MM-DD date.")
    arg_parser.add_argument("--repo", default=".", help="OpenVibeAI-data repository root.")
    arg_parser.add_argument("--dry-run", action="store_true", help="Validate and report planned writes only.")
    arg_parser.add_argument("--write", action="store_true", help="Write changed data files.")
    arg_parser.add_argument("--commit", action="store_true", help="Commit written data files; implies --write.")
    arg_parser.add_argument("--validate", action="store_true", help="Validate existing AI news JSON files.")
    return arg_parser


def main() -> None:
    args = parser().parse_args()
    if args.commit:
        args.write = True
    try:
        emit(run_publish(args))
    except subprocess.CalledProcessError as exc:
        stop("blocked", "command_failed", command=exc.cmd, error=str(exc))


if __name__ == "__main__":
    main()
