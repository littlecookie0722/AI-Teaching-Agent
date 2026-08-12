from pathlib import Path

from cli.dsl import load_schema, load_yaml, validate_dsl


ROOT = Path(__file__).resolve().parents[1]


def test_lab_example_matches_schema():
    validate_dsl(
        load_yaml(ROOT / "templates/lab/examples/basic-lab.yaml"),
        load_schema("lab", ROOT),
    )


def test_exam_example_matches_schema():
    validate_dsl(
        load_yaml(ROOT / "templates/exam/examples/notebook-fill-blank.yaml"),
        load_schema("exam", ROOT),
    )


def test_grading_example_matches_schema():
    grading = load_yaml(ROOT / "templates/grading/examples/python-pytest.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    plan = grading["spec"]["assessmentPlan"][0]
    assert plan["checkId"] == "check_pytest"
    assert plan["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY"
    assert plan["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"


def test_mixed_grading_example_matches_schema():
    grading = load_yaml(ROOT / "templates/grading/examples/mixed-checks.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    checks = grading["spec"]["checks"]
    plan = grading["spec"]["assessmentPlan"]
    assert [item["checkId"] for item in plan] == [item["id"] for item in checks]
    assert [item["type"] for item in plan] == [item["type"] for item in checks]
    assert all(item["executionPlan"]["requiredLimits"]["network"] == "disabled_by_default" for item in plan)


def test_readonly_sandbox_grading_example_matches_schema():
    grading = load_yaml(ROOT / "templates/grading/examples/readonly-sandbox.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    assert [check["type"] for check in grading["spec"]["checks"]] == [
        "file_exists",
        "json_field",
        "notebook_cell",
        "log_keyword",
        "pytest",
    ]
    assert grading["spec"]["assessmentPlan"][0]["riskLevel"] == "low"
    assert grading["spec"]["assessmentPlan"][2]["type"] == "pytest"
    assert grading["spec"]["assessmentPlan"][3]["type"] == "notebook_cell"
    assert grading["spec"]["assessmentPlan"][4]["type"] == "log_keyword"


def test_real_demo_notebook_static_plan_matches_schema():
    grading = load_yaml(ROOT / "examples/output/mimo-real-demo-notebook-static-plan.json")
    validate_dsl(grading, load_schema("grading", ROOT))
    assert [check["id"] for check in grading["spec"]["checks"]] == ["check_q2", "check_q3"]
    assert all(check["type"] == "notebook_cell" for check in grading["spec"]["checks"])


def test_ppt_example_matches_schema():
    validate_dsl(
        load_yaml(ROOT / "templates/ppt/examples/course-ppt.yaml"),
        load_schema("ppt", ROOT),
    )
