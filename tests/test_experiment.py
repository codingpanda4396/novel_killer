from __future__ import annotations

import json
import csv
import tempfile
from pathlib import Path

import pytest

from novelops.experiment import (
    create_experiment,
    load_experiment,
    save_experiment,
    list_experiments,
    experiment_path,
    import_metrics,
    generate_experiment_report,
    update_experiment_decision,
    concept_from_radar,
)


@pytest.fixture
def temp_project(tmp_path):
    project_dir = tmp_path / "projects" / "test_project"
    project_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        json.dumps({"name": "Test Project", "genre": "玄幻"}),
        encoding="utf-8",
    )
    return project_dir


def test_create_experiment(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    exp_dir = create_experiment("test_exp_001", "test_project", "qidian", "测试假设")
    assert exp_dir.exists()
    assert (exp_dir / "experiment.json").exists()
    assert (exp_dir / "hypothesis.md").exists()
    assert (exp_dir / "market_samples.md").exists()
    assert (exp_dir / "concept_package.md").exists()
    assert (exp_dir / "chapters").is_dir()


def test_create_experiment_no_overwrite(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("test_exp_002", "test_project", "qidian", "测试假设")
    with pytest.raises(FileExistsError):
        create_experiment("test_exp_002", "test_project", "qidian", "测试假设")


def test_load_experiment(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("test_exp_003", "test_project", "qidian", "测试假设")
    exp = load_experiment("test_project", "test_exp_003")
    assert exp["id"] == "test_exp_003"
    assert exp["project_id"] == "test_project"
    assert exp["platform_id"] == "qidian"
    assert exp["status"] == "drafting"
    assert exp["decision"] == "UNKNOWN"


def test_load_experiment_not_found(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    with pytest.raises(FileNotFoundError):
        load_experiment("test_project", "nonexistent")


def test_list_experiments(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("exp_a", "test_project", "qidian", "假设A")
    create_experiment("exp_b", "test_project", "fanqie", "假设B")

    experiments = list_experiments("test_project")
    assert "exp_a" in experiments
    assert "exp_b" in experiments


def test_save_experiment(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("test_exp_004", "test_project", "qidian", "测试假设")
    exp = load_experiment("test_project", "test_exp_004")
    exp["status"] = "collecting_data"
    save_experiment("test_project", "test_exp_004", exp)

    exp2 = load_experiment("test_project", "test_exp_004")
    assert exp2["status"] == "collecting_data"


def test_import_metrics(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("test_exp_005", "test_project", "qidian", "测试假设")

    csv_content = "date,platform,book_id,impressions,views,collections,favorites,income\n"
    csv_content += "2026-05-01,qidian,book001,5000,3000,150,80,15.5\n"
    csv_content += "2026-05-08,qidian,book001,6000,3500,180,100,22.0\n"

    csv_file = temp_project / "test_metrics.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    result = import_metrics("test_project", "test_exp_005", csv_file)
    assert result["success"] is True
    assert result["imported"] == 2

    exp_dir = temp_project / "experiments" / "test_exp_005"
    assert (exp_dir / "metrics.csv").exists()


def test_import_metrics_platform_mismatch(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("test_exp_006", "test_project", "qidian", "测试假设")

    csv_content = "date,platform,book_id,impressions\n"
    csv_content += "2026-05-01,fanqie,book001,5000\n"

    csv_file = temp_project / "test_wrong.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    result = import_metrics("test_project", "test_exp_006", csv_file)
    assert result["success"] is False
    assert any("platform mismatch" in err for err in result["errors"])


def test_generate_experiment_report(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("test_exp_007", "test_project", "qidian", "测试报告生成")
    report_path = generate_experiment_report("test_project", "test_exp_007")

    assert Path(report_path).exists()
    content = Path(report_path).read_text(encoding="utf-8")
    assert "test_exp_007" in content
    assert "起点中文网" in content


def test_update_experiment_decision_no_data(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("test_exp_008", "test_project", "qidian", "测试决策")
    decision = update_experiment_decision("test_project", "test_exp_008")
    assert decision == "UNKNOWN"


def test_concept_from_radar(temp_project, monkeypatch):
    monkeypatch.setattr("novelops.experiment.project_dir", lambda x: temp_project.parent / x)

    create_experiment("test_exp_009", "test_project", "qidian", "测试概念包")
    concept_path = concept_from_radar("test_project", "test_exp_009")

    assert Path(concept_path).exists()
    content = Path(concept_path).read_text(encoding="utf-8")
    assert "起点中文网" in content
    assert "qidian" in content
