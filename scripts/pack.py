"""Cross-platform packaging script for Adobe University Hackathon submission ZIP."""

import os
import sys
import zipfile

OUTPUT_ZIP = "brand-ai-readiness-audit.zip"
MAX_ALLOWED_MB = 50.0

EXCLUDE_PATTERNS = [
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "egg-info",
    ".venv",
    "tests",
    "docs",
    "gui",
    "config",
    "reports",
    "uv.lock",
    "VIDEO_SCRIPT.md",
    "SUBMISSION.md",
    "report.json",
    OUTPUT_ZIP,
    ".DS_Store",
]

INCLUDED_TOP_LEVEL = [
    "marketplace.json",
    "README.md",
    "LICENSE",
    "skills",
    "src",
    "requirements.txt",
    "pyproject.toml",
    "scripts",
]


def should_exclude(path: str) -> bool:
    norm = path.replace("\\", "/")
    for pat in EXCLUDE_PATTERNS:
        if pat in norm:
            return True
    return False


def create_package():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zip_path = os.path.join(repo_root, OUTPUT_ZIP)

    if os.path.exists(zip_path):
        os.remove(zip_path)

    print(f"Creating submission package at {zip_path}...")
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDED_TOP_LEVEL:
            item_path = os.path.join(repo_root, item)
            if not os.path.exists(item_path):
                continue

            if os.path.isfile(item_path):
                if not should_exclude(item):
                    zf.write(item_path, arcname=item)
                    file_count += 1
            elif os.path.isdir(item_path):
                for root, _, files in os.walk(item_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, repo_root)
                        if not should_exclude(rel_path):
                            zf.write(full_path, arcname=rel_path)
                            file_count += 1

    size_bytes = os.path.getsize(zip_path)
    size_mb = size_bytes / (1024 * 1024)
    print(f"Added {file_count} files.")
    print(f"Package Size: {size_mb:.2f} MB ({size_bytes} bytes)")

    if size_mb > MAX_ALLOWED_MB:
        print(f"ERROR: Submission zip exceeds {MAX_ALLOWED_MB} MB limit!")
        sys.exit(1)
    else:
        print(f"SUCCESS: Package is {size_mb:.2f} MB, safely below {MAX_ALLOWED_MB} MB limit.")


if __name__ == "__main__":
    create_package()
