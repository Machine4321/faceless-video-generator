"""Tests for shadowvault.utils.file_manager."""

import os
import pytest

from shadowvault.utils.file_manager import ensure_dirs, cleanup_files, archive_file


class TestEnsureDirs:
    def test_creates_single_directory(self, tmp_path):
        target = str(tmp_path / "new_dir")
        assert not os.path.exists(target)
        ensure_dirs(target)
        assert os.path.isdir(target)

    def test_creates_multiple_directories(self, tmp_path):
        d1 = str(tmp_path / "dir1")
        d2 = str(tmp_path / "dir2")
        d3 = str(tmp_path / "dir3")
        ensure_dirs(d1, d2, d3)
        assert os.path.isdir(d1)
        assert os.path.isdir(d2)
        assert os.path.isdir(d3)

    def test_existing_directory_no_error(self, tmp_path):
        target = str(tmp_path / "existing")
        os.makedirs(target)
        ensure_dirs(target)  # should not raise
        assert os.path.isdir(target)

    def test_nested_directory_creation(self, tmp_path):
        target = str(tmp_path / "a" / "b" / "c")
        ensure_dirs(target)
        assert os.path.isdir(target)

    def test_empty_string_skipped(self, tmp_path):
        ensure_dirs("", str(tmp_path / "valid"))
        assert os.path.isdir(str(tmp_path / "valid"))

    def test_no_args(self):
        ensure_dirs()  # should not raise


class TestCleanupFiles:
    def test_deletes_existing_files(self, tmp_path):
        f1 = tmp_path / "file1.mp4"
        f2 = tmp_path / "file2.mp3"
        f1.write_text("data")
        f2.write_text("data")
        deleted = cleanup_files([str(f1), str(f2)])
        assert deleted == 2
        assert not f1.exists()
        assert not f2.exists()

    def test_nonexistent_files_ignored(self, tmp_path):
        deleted = cleanup_files([str(tmp_path / "nope.txt")])
        assert deleted == 0

    def test_empty_string_ignored(self):
        deleted = cleanup_files(["", ""])
        assert deleted == 0

    def test_empty_list(self):
        deleted = cleanup_files([])
        assert deleted == 0

    def test_mixed_existing_and_missing(self, tmp_path):
        f1 = tmp_path / "exists.mp4"
        f1.write_text("data")
        deleted = cleanup_files([str(f1), str(tmp_path / "missing.mp4")])
        assert deleted == 1

    def test_directory_path_not_deleted(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        deleted = cleanup_files([str(d)])
        assert deleted == 0
        assert d.exists()


class TestArchiveFile:
    def test_moves_file_to_archive(self, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_text("video data")
        archive_dir = str(tmp_path / "archive")

        result = archive_file(str(src), archive_dir)
        assert result == os.path.join(archive_dir, "video.mp4")
        assert os.path.isfile(result)
        assert not src.exists()

    def test_creates_archive_dir_if_missing(self, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_text("data")
        archive_dir = str(tmp_path / "new_archive")

        archive_file(str(src), archive_dir)
        assert os.path.isdir(archive_dir)

    def test_empty_path_returns_original(self, tmp_path):
        result = archive_file("", str(tmp_path / "archive"))
        assert result == ""

    def test_nonexistent_file_returns_original(self, tmp_path):
        path = str(tmp_path / "missing.mp4")
        result = archive_file(path, str(tmp_path / "archive"))
        assert result == path

    def test_returns_original_on_move_failure(self, tmp_path, monkeypatch):
        src = tmp_path / "video.mp4"
        src.write_text("data")
        import shutil
        monkeypatch.setattr(shutil, "move", lambda *a, **kw: (_ for _ in ()).throw(OSError("fail")))

        result = archive_file(str(src), str(tmp_path / "archive"))
        assert result == str(src)
