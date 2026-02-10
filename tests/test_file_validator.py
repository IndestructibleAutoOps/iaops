"""Tests for the FileCheckValidator."""

from __future__ import annotations

from pathlib import Path

from indestructibleautoops.validation.file_validator import FileCheckValidator


class TestFileCheckValidator:
    def test_counts_files(self):
        project_root = str(Path(__file__).parent.parent)
        validator = FileCheckValidator(strict_mode=True)
        result = validator.validate({"project_root": project_root})
        assert result.metrics["source_file_count"] > 0

    def test_empty_project(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        validator = FileCheckValidator(strict_mode=True)
        result = validator.validate({"project_root": str(tmp_path)})
        assert result.metrics["source_file_count"] == 0

    def test_required_path_missing(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        validator = FileCheckValidator(
            strict_mode=True,
            required_paths=["src/main.py", "README.md"],
        )
        result = validator.validate({"project_root": str(tmp_path)})
        blocking = result.get_blocking_issues()
        assert len(blocking) == 2
        ids = {i.issue_id for i in blocking}
        assert "missing_required_path_src/main.py" in ids
        assert "missing_required_path_README.md" in ids

    def test_required_path_present(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "README.md").write_text("hello")
        validator = FileCheckValidator(
            strict_mode=True,
            required_paths=["README.md"],
        )
        result = validator.validate({"project_root": str(tmp_path)})
        missing_issues = [i for i in result.issues if "missing_required" in i.issue_id]
        assert len(missing_issues) == 0

    def test_detects_removed_files(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("# a")
        (src / "b.py").write_text("# b")

        validator = FileCheckValidator(strict_mode=True)

        # First run — establishes baseline
        validator.validate({"project_root": str(tmp_path)})

        # Remove a file
        (src / "b.py").unlink()

        # Second run — should detect removal
        result = validator.validate({"project_root": str(tmp_path)})
        removal_issues = [i for i in result.issues if "files_removed" in i.issue_id]
        assert len(removal_issues) == 1
        assert "b.py" in removal_issues[0].description

    def test_source_field_on_issues(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        validator = FileCheckValidator(
            strict_mode=True,
            required_paths=["nonexistent.py"],
        )
        result = validator.validate({"project_root": str(tmp_path)})
        for issue in result.issues:
            if "missing_required" in issue.issue_id:
                assert issue.source == "file_check"
