"""Fail CI when generated artifacts or obvious secrets enter the repository."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_DIRECTORY_NAMES = {
    ".gradle",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
}
FORBIDDEN_TOP_LEVEL_DIRECTORIES = {"artifacts", "cache", "data", "downloads", "logs", "reports"}
FORBIDDEN_FILE_NAMES = {".env", "local.properties"}
FORBIDDEN_SUFFIXES = {
    ".aab",
    ".apk",
    ".db",
    ".dll",
    ".exe",
    ".idsig",
    ".obj",
    ".pdb",
    ".pyc",
    ".pyo",
    ".sqlite",
    ".sqlite3",
    ".so",
    ".dylib",
}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".kt",
    ".kts",
    ".md",
    ".properties",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Bearer token": re.compile(
        r"(?i)authorization\s*[:=]\s*bearer\s+[A-Za-z0-9._~+/=-]{16,}"
    ),
    "assigned secret": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)"
        r"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{20,}"
    ),
}


def iter_repository_files() -> list[Path]:
    """Return tracked files, with a safe fallback outside a Git checkout."""

    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        files: list[Path] = []
        for path in ROOT.rglob("*"):
            relative = path.relative_to(ROOT)
            if ".git" in relative.parts:
                continue
            if set(relative.parts[:-1]) & FORBIDDEN_DIRECTORY_NAMES:
                continue
            if path.is_file():
                files.append(path)
        return files

    return [
        ROOT / raw_path.decode("utf-8")
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    ]


def main() -> int:
    errors: list[str] = []

    for path in iter_repository_files():
        relative = path.relative_to(ROOT)
        parent_names = set(relative.parts[:-1])

        forbidden_parents = parent_names & FORBIDDEN_DIRECTORY_NAMES
        if forbidden_parents:
            errors.append(
                f"generated/cache directory is tracked: {relative} "
                f"({', '.join(sorted(forbidden_parents))})"
            )

        if relative.parts and relative.parts[0] in FORBIDDEN_TOP_LEVEL_DIRECTORIES:
            errors.append(f"runtime/output directory is tracked: {relative}")

        if path.name in FORBIDDEN_FILE_NAMES:
            errors.append(f"local configuration is tracked: {relative}")

        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"generated/binary artifact is tracked: {relative}")

        if path.stat().st_size > 1_000_000 or path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"possible {label} in {relative}")

    if errors:
        print("repository hygiene check failed:", file=sys.stderr)
        for error in sorted(set(errors)):
            print(f"- {error}", file=sys.stderr)
        return 1

    print("repository hygiene check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
