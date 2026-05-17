"""
shadowvault/utils/file_manager.py
Temp directory management, cleanup, and archive helpers.
"""

from __future__ import annotations

import logging
import os
import shutil

logger = logging.getLogger(__name__)


def ensure_dirs(*dirs: str) -> None:
    """Create directories if they don't exist."""
    for d in dirs:
        if d:
            os.makedirs(d, exist_ok=True)


def cleanup_files(paths: list[str]) -> int:
    """
    Delete a list of file paths. Returns the count of successfully deleted files.
    Logs warnings for files that can't be deleted but does not raise.
    """
    deleted = 0
    for path in paths:
        if path and os.path.isfile(path):
            try:
                os.remove(path)
                logger.debug("Deleted temp file: %s", path)
                deleted += 1
            except OSError as exc:
                logger.warning("Could not delete %s: %s", path, exc)
    return deleted


def archive_file(file_path: str, archive_folder: str) -> str:
    """
    Move a file to the archive folder.
    Returns the new path on success, or the original path on failure.
    """
    if not file_path or not os.path.isfile(file_path):
        return file_path

    os.makedirs(archive_folder, exist_ok=True)
    dest = os.path.join(archive_folder, os.path.basename(file_path))
    try:
        shutil.move(file_path, dest)
        logger.info("Archived: %s -> %s", file_path, dest)
        return dest
    except Exception as exc:
        logger.warning("Archive move failed (%s) - file stays at %s", exc, file_path)
        return file_path
