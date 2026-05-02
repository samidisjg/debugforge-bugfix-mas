from __future__ import annotations

from pathlib import Path
import difflib
import shutil


def normalize_generated_code(new_code: str) -> str:
    """Clean generated code formatting without changing program behavior."""
    lines = [line.rstrip() for line in new_code.replace("\r\n", "\n").replace("\r", "\n").split("\n")]

    cleaned: list[str] = []
    blank_streak = 0
    for line in lines:
        if line.strip() == "":
            blank_streak += 1
            if blank_streak <= 1:
                cleaned.append("")
            continue
        blank_streak = 0
        cleaned.append(line)

    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    normalized = "\n".join(cleaned)
    if normalized:
        normalized += "\n"
    return normalized


def write_replacement_file(target_file: str, new_code: str) -> str:
    """Replace the target file with normalized code and return the updated path."""
    path = Path(target_file)
    if not path.exists():
        raise FileNotFoundError(f"Target file does not exist: {target_file}")
    path.write_text(normalize_generated_code(new_code), encoding="utf-8")
    return str(path)


def create_backup_file(target_file: str) -> str:
    """Create a backup copy of the target file and return the backup path."""
    path = Path(target_file)
    if not path.exists():
        raise FileNotFoundError(f"Target file does not exist: {target_file}")
    backup_path = path.with_suffix(path.suffix + ".bak")
    shutil.copyfile(path, backup_path)
    return str(backup_path)


def restore_backup_file(target_file: str, backup_file: str) -> str:
    """Restore the original file from a backup copy."""
    target_path = Path(target_file)
    backup_path = Path(backup_file)
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file does not exist: {backup_file}")
    shutil.copyfile(backup_path, target_path)
    return str(target_path)


def write_patch_diff(output_path: str, original_code: str, new_code: str, filename: str) -> str:
    """Write a unified diff for the normalized patch and return the diff path."""
    diff_path = Path(output_path)
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_new_code = normalize_generated_code(new_code)
    diff = difflib.unified_diff(
        original_code.splitlines(),
        normalized_new_code.splitlines(),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    diff_path.write_text("\n".join(diff) + "\n", encoding="utf-8")
    return str(diff_path)
