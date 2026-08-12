import json
import os
from pathlib import Path

import pytest

from providers import (
    ProviderError,
    RealLlmDemoDslRequest,
    build_real_llm_demo_dsl_error_context,
    run_real_llm_demo_dsl_generation,
)
from providers.real_llm_demo_dsl import build_real_llm_schema_failure_diagnostic
from sandbox.grade_runner import GradingRunner
from sandbox.real_sandbox_precheck import build_real_sandbox_precheck_report


ROOT = Path(__file__).resolve().parents[1]
ONLINE_SMOKE_ENV = "LAB_REAL_LLM_ONLINE_SMOKE"
ONLINE_SMOKE_MODEL_ENV = "LAB_REAL_LLM_ONLINE_SMOKE_MODEL"
ONLINE_SMOKE_BASE_URL_ENV = "LAB_REAL_LLM_ONLINE_SMOKE_BASE_URL"
ONLINE_SMOKE_API_SURFACE_ENV = "LAB_REAL_LLM_ONLINE_SMOKE_API_SURFACE"
ONLINE_SMOKE_MAX_OUTPUT_TOKENS_ENV = "LAB_REAL_LLM_ONLINE_SMOKE_MAX_OUTPUT_TOKENS"
ONLINE_SMOKE_TIMEOUT_ENV = "LAB_REAL_LLM_ONLINE_SMOKE_TIMEOUT_SECONDS"


def valid_exam_dsl():
    return {
        "version": "1.0",
        "kind": "Exam",
        "metadata": {
            "id": "exam-real-demo-provider-test",
            "title": "真实 LLM Demo Provider 测试试题",
            "sourceLabId": "lab-real-demo-provider-test",
            "difficulty": "beginner",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "questionType": "coding_task",
            "totalScore": 100,
            "questions": [
                {
                    "id": "q1",
                    "title": "确认审核状态",
                    "stem": "请输出 WAITING_REVIEW。",
                    "score": 100,
                    "gradingRef": "check_waiting_review",
                }
            ],
        },
    }


def exam_dsl_with_question_string_field_drift():
    exam = valid_exam_dsl()
    exam["spec"]["totalScore"] = 100
    exam["spec"]["questions"] = [
        {
            "id": "q1",
            "title": "对象字段漂移",
            "stem": "完成题目 1",
            "score": 25,
            "answer": {"text": "WAITING_REVIEW"},
            "gradingRef": {"id": "check_q1"},
        },
        {
            "id": "q2",
            "title": "数组字段漂移",
            "stem": "完成题目 2",
            "score": 25,
            "answer": ["步骤一", "步骤二"],
            "gradingRef": ["check_q2"],
        },
        {
            "id": "q3",
            "title": "数字字段漂移",
            "stem": "完成题目 3",
            "score": 25,
            "answer": 42,
            "gradingRef": {"ref": "check_q3"},
        },
        {
            "id": "q4",
            "title": "嵌套字段漂移",
            "stem": "完成题目 4",
            "score": 25,
            "answer": {"items": ["A", "B"]},
            "gradingRef": {"description": "check_q4"},
        },
    ]
    return exam


def exam_dsl_with_question_type_and_score_drift():
    exam = valid_exam_dsl()
    exam["spec"]["questionType"] = "unit_test"
    exam["spec"]["totalScore"] = "100 points"
    exam["spec"]["questions"] = [
        {
            "id": "q1",
            "title": "字符串分值",
            "stem": "完成题目 1",
            "score": "40 分",
            "gradingRef": "check_q1",
        },
        {
            "id": "q2",
            "title": "零分漂移",
            "stem": "完成题目 2",
            "score": 0,
            "gradingRef": "check_q2",
        },
        {
            "id": "q3",
            "title": "缺失分值",
            "stem": "完成题目 3",
            "gradingRef": "check_q3",
        },
    ]
    return exam


def exam_dsl_with_answer_like_grading_refs():
    exam = valid_exam_dsl()
    exam["spec"]["totalScore"] = 10
    exam["spec"]["questions"] = [
        {
            "id": "q1",
            "title": "插件状态确认",
            "stem": "说明如何确认 VS Code 插件已启用。",
            "score": 2,
            "gradingRef": "方法一：查看扩展图标；方法二：观察状态栏图标。",
        },
        {
            "id": "q2",
            "title": "代码补全",
            "stem": "补全 greet 函数。",
            "score": 4,
            "gradingRef": "def greet(name, greeting='Hello'):\n    return f\"{greeting}, {name}!\"",
        },
        {
            "id": "q3",
            "title": "默认参数",
            "stem": "写出默认问候语。",
            "score": 2,
            "gradingRef": "'Hello'",
        },
        {
            "id": "q4",
            "title": "测试用例",
            "stem": "列出测试调用和预期输出。",
            "score": 2,
            "answer": "已有答案应优先保留",
            "gradingRef": "测试调用1: greet('Alice', 'Hi')，预期输出: 'Hi, Alice!'",
        },
    ]
    return exam


def exam_dsl_with_generic_manual_grading_refs():
    exam = valid_exam_dsl()
    exam["spec"]["totalScore"] = 100
    exam["spec"]["questions"] = [
        {"id": "q1", "title": "环境检查", "stem": "检查环境。", "score": 20, "gradingRef": "manual"},
        {"id": "q2", "title": "阅读代码", "stem": "阅读示例代码。", "score": 20, "gradingRef": "manual"},
        {"id": "q3", "title": "修改代码", "stem": "使用 AI 修改代码。", "score": 30, "gradingRef": "manual"},
        {"id": "q4", "title": "运行测试", "stem": "运行测试。", "score": 30, "gradingRef": "manual"},
    ]
    return exam


def exam_dsl_without_questions_but_custom_total_score():
    exam = valid_exam_dsl()
    exam["spec"]["totalScore"] = 30
    exam["spec"].pop("questions")
    return exam


def lab_dsl_with_shape_drift():
    return {
        "version": "1.0",
        "kind": "Lab",
        "metadata": {
            "id": "lab-real-demo-provider-test",
            "title": "真实 LLM Demo Provider 测试实验",
            "description": "模型额外生成的描述字段",
            "targetUsers": ["平台开发者"],
            "difficulty": "beginner",
            "durationMinutes": 45,
            "tags": ["LLM"],
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "objectives": ["验证 DSL 形状归一化"],
            "targetUsers": ["平台开发者"],
            "environment": {"description": "Notebook 环境"},
            "steps": [{"title": "审核生成内容", "instruction": "确认状态"}],
        },
    }


def lab_dsl_with_metadata_and_list_drift():
    lab = lab_dsl_with_shape_drift()
    lab["metadata"].update(
        {
            "id": {"value": "lab-real-demo-provider-test"},
            "title": {"text": "真实 LLM Demo Provider 测试实验"},
            "category": ["AI", "实训"],
            "difficulty": "easy",
            "durationMinutes": "45 minutes",
            "tags": "LLM, Python；Notebook",
        }
    )
    lab["spec"]["objectives"] = [{"text": "理解 WAITING_REVIEW"}, "完成人工审核"]
    lab["spec"]["targetUsers"] = "教师,学生；平台开发者"
    return lab


def lab_dsl_with_materials_type_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["materials"] = ["examples/input/demo-source.md", "实验讲义"]
    return lab


def lab_dsl_with_environment_resources_type_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["environment"]["resources"] = "2 CPU / 4GB memory"
    return lab


def lab_dsl_with_environment_resource_value_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["environment"]["resources"] = {"cpu": "2", "memoryGb": 0, "gpu": 1}
    return lab


def lab_dsl_with_environment_resource_alias_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["environment"]["resources"] = {
        "cpuCores": "3 cores",
        "memory": "8 GB",
        "diskGb": 20,
    }
    return lab


def lab_dsl_with_rich_materials_and_step_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["materials"] = [
        {"kind": "markdown", "file": "examples/input/demo-source.md"},
        {"format": "pdf", "name": {"text": "课程讲义.pdf"}},
    ]
    lab["spec"]["steps"] = [
        {
            "id": 1,
            "title": {"text": "环境检查"},
            "instruction": ["检查 Python", "记录版本"],
            "commands": "python --version, pip --version",
            "expectedResult": {"text": "输出版本号"},
        }
    ]
    return lab


def lab_dsl_with_grading_ref_shape_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["grading"] = {"id": "grading_real_demo_lab", "title": "评分规则"}
    return lab


def lab_dsl_with_materials_and_steps_map_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["materials"] = {
        "source": "examples/input/demo-source.md",
        "guide": {"kind": "markdown", "file": "guides/review.md"},
    }
    lab["spec"]["steps"] = {
        "step_review": {
            "title": "审核生成内容",
            "instruction": {"text": "确认 WAITING_REVIEW"},
            "commands": "python lab_cli.py review list",
        },
        "step_record": "记录审核结论",
    }
    return lab


def lab_dsl_with_step_alias_field_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["steps"] = [
        {
            "id": "step_alias_1",
            "name": "检查运行环境",
            "description": {"text": "确认 Python 与 pytest 可用。"},
            "shellCommands": "python --version, pytest --version",
            "expected": {"text": "输出版本号"},
        },
        {
            "stepId": "step_alias_2",
            "heading": "执行示例脚本",
            "content": ["运行示例", "记录 WAITING_REVIEW 输出"],
            "cmds": ["python main.py", {"text": "python -m pytest"}],
            "successCriteria": ["看到 WAITING_REVIEW", "pytest passed"],
        },
    ]
    return lab


def lab_dsl_with_parseable_resource_text_drift():
    lab = lab_dsl_with_shape_drift()
    lab["spec"]["environment"]["resources"] = "CPU 3 / Memory 6GB"
    return lab


def lab_dsl_with_top_level_aliases():
    return {
        "version": "1.0",
        "kind": "Lab",
        "metadata": {
            "id": "lab-alias-demo",
            "title": "字段别名实验",
            "level": "medium",
            "estimatedMinutes": "50 minutes",
            "keywords": "Python, Notebook",
        },
        "status": "WAITING_REVIEW",
        "learningObjectives": ["理解字段别名归一化"],
        "audience": ["教师", "学生"],
        "runtimeEnvironment": {
            "type": "notebook",
            "image": "python:3.11",
            "resources": "CPU 2 / Memory 4GB",
        },
        "tasks": [
            {
                "title": "完成实验步骤",
                "instruction": "阅读并审核生成内容。",
            }
        ],
    }


def exam_dsl_with_spec_aliases():
    return {
        "version": "1.0",
        "kind": "Exam",
        "metadata": {
            "id": "exam-alias-demo",
            "title": "字段别名试题",
            "labId": "lab-alias-demo",
            "level": "medium",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "type": "short-answer",
            "totalPoints": "100 points",
            "items": [
                {
                    "id": "q1",
                    "title": "说明审核边界",
                    "stem": "说明为什么 AI 生成内容需要人工审核。",
                    "gradingRef": "check_review_boundary",
                },
                {
                    "id": "q2",
                    "title": "说明导入边界",
                    "stem": "说明为什么真实导入前需要 dry-run。",
                    "gradingRef": "check_import_boundary",
                },
            ],
        },
    }


def exam_dsl_with_top_level_questions():
    return {
        "version": "1.0",
        "kind": "Exam",
        "metadata": {
            "id": "exam-top-level-questions-demo",
            "title": "顶层题目试题",
            "sourceLabId": "lab-real-demo-provider-test",
            "difficulty": "beginner",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "questionType": "coding_task",
            "totalScore": 100,
        },
        "questions": [
            {
                "id": "q1",
                "title": "顶层题目一",
                "stem": "说明审核状态。",
                "score": 60,
                "gradingRef": "check_q1",
            },
            {
                "id": "q2",
                "title": "顶层题目二",
                "stem": "说明导入预览。",
                "score": 40,
                "gradingRef": "check_q2",
            },
        ],
    }


def exam_dsl_with_question_map_drift():
    exam = valid_exam_dsl()
    exam["spec"]["questionType"] = "short_answer"
    exam["spec"]["totalScore"] = 100
    exam["spec"]["questions"] = {
        "q_review": {
            "title": "说明审核边界",
            "stem": "说明为什么生成内容必须等待人工审核。",
            "score": "40 分",
            "gradingRef": {"id": "check_review"},
        },
        "q_import": {
            "title": "说明导入边界",
            "stem": "说明为什么真实导入前需要 dry-run。",
            "score": 60,
            "gradingRef": "check_import",
        },
    }
    return exam


def exam_dsl_with_question_alias_field_drift():
    exam = valid_exam_dsl()
    exam["spec"]["questionType"] = "coding_task"
    exam["spec"]["totalScore"] = 100
    exam["spec"]["questions"] = [
        {
            "id": "q_alias_1",
            "name": "用 question 字段承载题目标题",
            "question": "请补全 main.py，让程序输出 WAITING_REVIEW。",
            "starterCode": {"text": "print(____)"},
            "correctAnswer": {"text": "WAITING_REVIEW"},
            "checkId": {"id": "check_waiting_review"},
            "score": "50 分",
        },
        {
            "id": "q_alias_2",
            "heading": "用 prompt 字段承载题干",
            "prompt": ["运行 pytest", "确认所有用例通过"],
            "referenceAnswer": ["pytest", "passed"],
            "rubricRef": "check_pytest_passed",
            "score": 50,
        },
    ]
    return exam


def grading_dsl_with_spec_aliases():
    return {
        "version": "1.0",
        "kind": "Grading",
        "metadata": {
            "id": "grading-alias-demo",
            "title": "字段别名评分",
            "examId": "exam-alias-demo",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "totalPoints": "100 points",
            "timeout": "45 seconds",
            "gradingRules": [
                {"id": "check_review_boundary", "type": "stdout", "score": "60 points"},
                {"id": "check_import_boundary", "type": "log", "score": "40 points"},
            ],
        },
    }


def grading_dsl_with_runner_field_drift():
    return {
        "version": "1.0",
        "kind": "Grading",
        "metadata": {
            "id": "grading-real-demo-provider-test",
            "title": "真实 LLM Demo Provider 测试评分",
            "sourceExamId": "exam-real-demo-provider-test",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "totalScore": 100,
            "timeoutSeconds": 30,
            "checks": [
                {"id": "check_q1", "type": "stdout_contains", "score": 20},
                {"id": "check_q2", "type": "notebook_cell", "score": 30, "notebookPath": "demo.ipynb"},
                {"id": "check_q3", "type": "json_field", "score": 30, "path": "metrics.json"},
                {"id": "check_q4", "type": "pytest", "score": 20},
            ],
            "assessmentPlan": [
                {
                    "checkId": "check_q1",
                    "type": "stdout_contains",
                    "runner": "StdoutContainsGrader",
                    "score": 20,
                    "inputSummary": "LLM omitted command and expected tokens.",
                    "executionPlan": {
                        "strategy": "MOCK_PLAN_ONLY",
                        "requiredLimits": {
                            "cpu": "required",
                            "memory": "required",
                            "timeout": "30s",
                            "network": "disabled_by_default",
                            "filesystem": "isolated_workspace_required",
                            "process": "limited",
                        },
                        "wouldRunInsideRealSandbox": True,
                    },
                    "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                    "riskLevel": "medium",
                    "sandboxRequiredBeforeRealExecution": True,
                },
                {
                    "checkId": "check_q2",
                    "type": "notebook_cell",
                    "runner": "NotebookGrader",
                    "score": 30,
                    "inputSummary": "LLM omitted cellIndex and expected tokens.",
                    "executionPlan": {
                        "strategy": "MOCK_PLAN_ONLY",
                        "requiredLimits": {
                            "cpu": "required",
                            "memory": "required",
                            "timeout": "30s",
                            "network": "disabled_by_default",
                            "filesystem": "isolated_workspace_required",
                            "process": "limited",
                        },
                        "wouldRunInsideRealSandbox": True,
                    },
                    "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                    "riskLevel": "high",
                    "sandboxRequiredBeforeRealExecution": True,
                },
                {
                    "checkId": "check_q3",
                    "type": "json_field",
                    "runner": "JsonFieldGrader",
                    "score": 30,
                    "inputSummary": "LLM omitted jsonPath and expectedValue.",
                    "executionPlan": {
                        "strategy": "MOCK_PLAN_ONLY",
                        "requiredLimits": {
                            "cpu": "required",
                            "memory": "required",
                            "timeout": "30s",
                            "network": "disabled_by_default",
                            "filesystem": "isolated_workspace_required",
                            "process": "limited",
                        },
                        "wouldRunInsideRealSandbox": True,
                    },
                    "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                    "riskLevel": "low",
                    "sandboxRequiredBeforeRealExecution": True,
                },
                {
                    "checkId": "check_q4",
                    "type": "pytest",
                    "runner": "PytestGrader",
                    "score": 20,
                    "inputSummary": "LLM omitted pytest path.",
                    "executionPlan": {
                        "strategy": "MOCK_PLAN_ONLY",
                        "requiredLimits": {
                            "cpu": "required",
                            "memory": "required",
                            "timeout": "30s",
                            "network": "disabled_by_default",
                            "filesystem": "isolated_workspace_required",
                            "process": "limited",
                        },
                        "wouldRunInsideRealSandbox": True,
                    },
                    "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                    "riskLevel": "medium",
                    "sandboxRequiredBeforeRealExecution": True,
                },
            ],
        },
    }


def grading_dsl_with_required_limits_type_drift():
    grading = grading_dsl_with_runner_field_drift()
    limits = grading["spec"]["assessmentPlan"][0]["executionPlan"]["requiredLimits"]
    limits["cpu"] = 1
    limits["memory"] = ""
    limits["timeout"] = {"seconds": 30}
    return grading


def grading_dsl_with_metadata_string_field_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["metadata"] = {
        "id": {"value": "grading-real-demo-provider-test"},
        "title": {"text": "真实 LLM Demo Provider 测试评分"},
        "sourceExamId": ["exam-real-demo-provider-test"],
    }
    return grading


def grading_dsl_with_check_string_field_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["checks"] = [
        {
            "id": {"value": "check_stdout"},
            "type": "stdout_contains",
            "command": {"text": "python main.py"},
            "expected": "WAITING_REVIEW",
            "score": 40,
        },
        {
            "id": 2,
            "type": "file_exists",
            "path": ["result.csv"],
            "score": 30,
        },
        {
            "id": {"id": "check_json"},
            "type": "json_field",
            "path": {"path": "metrics.json"},
            "jsonPath": {"value": "$.score"},
            "expectedValue": 1,
            "score": 30,
        },
    ]
    grading["spec"]["assessmentPlan"] = []
    return grading


def grading_dsl_with_check_alias_field_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["totalScore"] = 100
    grading["spec"]["checks"] = [
        {
            "checkId": "check_stdout_alias",
            "checkType": "stdout",
            "cmd": {"text": "python main.py"},
            "expectedOutput": ["WAITING_REVIEW", {"text": "PASS"}],
            "points": 50,
        },
        {
            "ruleId": "check_file_alias",
            "kind": "file",
            "filePath": ["result.csv"],
            "points": 25,
        },
        {
            "name": "check_json_alias",
            "runner": "JsonFieldGrader",
            "filePath": {"path": "metrics.json"},
            "fieldPath": {"value": "$.score"},
            "expectedJsonValue": {"value": 0.9},
            "weight": 25,
        },
    ]
    grading["spec"]["assessmentPlan"] = []
    return grading


def grading_dsl_with_question_id_check_refs():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["totalScore"] = 30
    grading["spec"]["checks"] = [
        {"id": "q1-intro", "type": "stdout_contains", "command": "python main.py", "expected": ["AI"], "score": 10},
        {"id": "q2-code", "type": "stdout_contains", "command": "python main.py", "expected": ["squares"], "score": 10},
        {"id": "q3-test", "type": "stdout_contains", "command": "python -m pytest", "expected": ["passed"], "score": 10},
    ]
    grading["spec"]["assessmentPlan"] = [
        {
            "checkId": "q1-intro",
            "type": "stdout_contains",
            "runner": "StdoutContainsGrader",
            "score": 10,
            "inputSummary": "Check AI assistant concepts.",
            "executionPlan": {
                "strategy": "MOCK_PLAN_ONLY",
                "requiredLimits": {
                    "cpu": "required",
                    "memory": "required",
                    "timeout": "30s",
                    "network": "disabled_by_default",
                    "filesystem": "isolated_workspace_required",
                    "process": "limited",
                },
                "wouldRunInsideRealSandbox": True,
            },
            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
            "riskLevel": "low",
            "sandboxRequiredBeforeRealExecution": True,
        },
        {
            "checkId": "q2-code",
            "type": "stdout_contains",
            "runner": "StdoutContainsGrader",
            "score": 10,
            "inputSummary": "Check list comprehension.",
            "executionPlan": {
                "strategy": "MOCK_PLAN_ONLY",
                "requiredLimits": {
                    "cpu": "required",
                    "memory": "required",
                    "timeout": "30s",
                    "network": "disabled_by_default",
                    "filesystem": "isolated_workspace_required",
                    "process": "limited",
                },
                "wouldRunInsideRealSandbox": True,
            },
            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
            "riskLevel": "medium",
            "sandboxRequiredBeforeRealExecution": True,
        },
        {
            "checkId": "q3-test",
            "type": "stdout_contains",
            "runner": "StdoutContainsGrader",
            "score": 10,
            "inputSummary": "Check pytest command.",
            "executionPlan": {
                "strategy": "MOCK_PLAN_ONLY",
                "requiredLimits": {
                    "cpu": "required",
                    "memory": "required",
                    "timeout": "30s",
                    "network": "disabled_by_default",
                    "filesystem": "isolated_workspace_required",
                    "process": "limited",
                },
                "wouldRunInsideRealSandbox": True,
            },
            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
            "riskLevel": "medium",
            "sandboxRequiredBeforeRealExecution": True,
        },
    ]
    return grading


def grading_dsl_with_single_generic_check():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["totalScore"] = 100
    grading["spec"]["checks"] = [
        {
            "id": "check_waiting_review",
            "type": "stdout_contains",
            "command": "python main.py",
            "expected": ["WAITING_REVIEW"],
            "score": 100,
        }
    ]
    grading["spec"]["assessmentPlan"] = [
        {
            "checkId": "check_waiting_review",
            "type": "stdout_contains",
            "runner": "StdoutContainsGrader",
            "score": 100,
            "inputSummary": "Plan stdout check for command: python main.py",
            "executionPlan": {
                "strategy": "MOCK_PLAN_ONLY",
                "requiredLimits": {
                    "cpu": "required",
                    "memory": "required",
                    "timeout": "30s",
                    "network": "disabled_by_default",
                    "filesystem": "isolated_workspace_required",
                    "process": "limited",
                },
                "wouldRunInsideRealSandbox": True,
            },
            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
            "riskLevel": "medium",
            "sandboxRequiredBeforeRealExecution": True,
        }
    ]
    return grading


def grading_dsl_with_assessment_plan_input_summary_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["checks"] = [
        {"id": "check_stdout", "type": "stdout_contains", "command": "python main.py", "score": 50},
        {"id": "check_pytest", "type": "pytest", "path": "tests/test_main.py", "score": 50},
    ]
    grading["spec"]["assessmentPlan"] = [
        {
            "checkId": "check_stdout",
            "type": "stdout_contains",
            "runner": "StdoutContainsGrader",
            "score": 50,
            "inputSummary": {"text": "检查命令输出包含 WAITING_REVIEW"},
            "executionPlan": {
                "strategy": "MOCK_PLAN_ONLY",
                "requiredLimits": {
                    "cpu": "required",
                    "memory": "required",
                    "timeout": "30s",
                    "network": "disabled_by_default",
                    "filesystem": "isolated_workspace_required",
                    "process": "limited",
                },
                "wouldRunInsideRealSandbox": True,
            },
            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
            "riskLevel": "medium",
            "sandboxRequiredBeforeRealExecution": True,
        },
        {
            "checkId": "check_pytest",
            "type": "pytest",
            "runner": "PytestGrader",
            "score": 50,
            "inputSummary": "",
            "executionPlan": {
                "strategy": "MOCK_PLAN_ONLY",
                "requiredLimits": {
                    "cpu": "required",
                    "memory": "required",
                    "timeout": "30s",
                    "network": "disabled_by_default",
                    "filesystem": "isolated_workspace_required",
                    "process": "limited",
                },
                "wouldRunInsideRealSandbox": True,
            },
            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
            "riskLevel": "medium",
            "sandboxRequiredBeforeRealExecution": True,
        },
    ]
    return grading


def grading_dsl_with_assessment_plan_alias_field_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["checks"] = [
        {
            "id": "check_stdout",
            "type": "stdout_contains",
            "command": "python main.py",
            "expected": ["WAITING_REVIEW"],
            "score": 50,
        },
        {"id": "check_pytest", "type": "pytest", "path": "tests/test_main.py", "score": 50},
    ]
    grading["spec"]["assessmentPlan"] = [
        {
            "check_id": "check_pytest",
            "checkType": "unit_test",
            "grader": "PytestGrader",
            "points": 50,
            "summary": {"text": "运行 pytest 校验答案"},
            "execution": {
                "mode": "REAL_EXECUTION",
                "limits": {"cpu": 1, "memory": "", "timeout": {"seconds": 30}},
                "wouldRunInSandbox": False,
            },
            "evidence": {"status": "PASSED", "stdout": "fake evidence"},
            "risk": "critical",
            "sandboxRequired": False,
        },
        {
            "check_id": "check_stdout",
            "kind": "stdout",
            "summary": "检查命令输出包含 WAITING_REVIEW",
            "runPlan": {"limits": {"network": "enabled"}},
        },
    ]
    return grading


def grading_dsl_with_assessment_plan_mock_evidence_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["checks"] = [
        {"id": "check_stdout", "type": "stdout_contains", "command": "python main.py", "score": 50},
        {"id": "check_pytest", "type": "pytest", "path": "tests/test_main.py", "score": 50},
    ]
    grading["spec"]["assessmentPlan"][0]["mockEvidence"] = "collected by llm"
    grading["spec"]["assessmentPlan"][1]["mockEvidence"] = {
        "status": {"text": "PASSED"},
        "stdout": "WAITING_REVIEW",
    }
    return grading


def grading_dsl_with_check_type_alias_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["checks"] = [
        {"id": "check_q1", "type": "stdout", "score": 20},
        {"id": "check_q2", "type": "unit_test", "score": 30},
        {"id": "check_q3", "type": "notebook", "score": 30},
        {"id": "check_q4", "type": "json_path", "score": 10},
        {"id": "check_q5", "type": "log", "score": 10},
    ]
    grading["spec"]["assessmentPlan"] = []
    return grading


def grading_dsl_with_expected_token_type_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["checks"] = [
        {
            "id": "check_q1",
            "type": "stdout_contains",
            "command": "python main.py",
            "expected": [{"text": "WAITING_REVIEW"}, 42, ["A", "B"]],
            "score": 100,
        }
    ]
    grading["spec"]["assessmentPlan"] = []
    return grading


def grading_dsl_with_check_and_assessment_plan_map_drift():
    grading = grading_dsl_with_runner_field_drift()
    grading["spec"]["totalScore"] = 100
    grading["spec"]["checks"] = {
        "check_review": {
            "type": "stdout",
            "command": {"text": "python main.py"},
            "expected": {"text": "WAITING_REVIEW"},
            "score": "40 points",
        },
        "check_pytest": {
            "type": "unit_test",
            "path": {"path": "tests/test_main.py"},
            "score": 60,
        },
    }
    grading["spec"]["assessmentPlan"] = {
        "check_review": {
            "inputSummary": {"text": "检查审核状态"},
            "executionPlan": {
                "requiredLimits": {
                    "cpu": 1,
                    "timeout": {"seconds": 30},
                }
            },
            "mockEvidence": "LLM claimed collected evidence",
        },
        "check_pytest": "运行 pytest 评分计划",
    }
    return grading


def ppt_dsl_with_slide_shape_drift():
    return {
        "version": "1.0",
        "kind": "PPT",
        "metadata": {
            "id": {"value": "ppt-real-demo-provider-test"},
            "title": "真实 LLM Demo Provider 测试课件",
            "audience": {"text": "平台开发者"},
            "durationMinutes": "45 minutes",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "theme": {"style": {"name": "clean"}, "language": {"value": "zh-CN"}},
            "slides": [
                {
                    "id": 1,
                    "type": "cover",
                    "title": {"text": "演示封面"},
                    "subtitle": ["真实 LLM", "DSL 审核"],
                    "bullets": "统一进入 WAITING_REVIEW",
                },
                {
                    "type": "conclusion",
                    "title": "总结",
                    "bullets": [{"text": "不自动发布"}, {"description": "人工审核后再进入平台实体"}],
                },
            ],
        },
    }


def ppt_dsl_with_slide_notes_and_duration_drift():
    ppt = ppt_dsl_with_slide_shape_drift()
    ppt["spec"]["slides"] = [
        {
            "id": {"value": "cover"},
            "type": "front-page",
            "title": {"text": "课程封面"},
            "speakerNotes": "强调课程目标和人工审核边界。",
            "durationSeconds": "90 seconds",
        },
        {
            "type": "wrap-up",
            "title": "总结",
            "bullets": [{"text": "复盘 DSL 生成"}, "保持 WAITING_REVIEW"],
            "notes": ["提醒审核 PPTX Artifact", "不要自动发布"],
            "duration": 120,
        },
    ]
    return ppt


def ppt_dsl_with_named_string_field_drift():
    ppt = ppt_dsl_with_slide_shape_drift()
    ppt["metadata"]["title"] = {"title": "PPT 标题字段对象"}
    ppt["metadata"]["audience"] = {"audience": "教师"}
    ppt["spec"]["slides"][0]["title"] = {"title": "封面标题字段对象"}
    ppt["spec"]["slides"][0]["subtitle"] = {"subtitle": "副标题字段对象"}
    return ppt


def ppt_dsl_with_slide_alias_field_drift():
    ppt = ppt_dsl_with_slide_shape_drift()
    ppt["spec"]["slides"] = [
        {
            "slideId": "goals",
            "layout": "content-page",
            "heading": "学习目标",
            "points": [{"text": "理解真实 LLM 产物校验"}, "保持 WAITING_REVIEW"],
            "speaker_notes": "只做人工审核前预览。",
        },
        {
            "key": "recap",
            "kind": "wrap-up",
            "name": "总结与下一步",
            "items": ["复盘 Schema 漂移", {"description": "记录下一步建议"}],
        },
    ]
    return ppt


def ppt_dsl_with_spec_aliases():
    return {
        "version": "1.0",
        "kind": "PPT",
        "metadata": {
            "id": "ppt-alias-demo",
            "title": "字段别名课件",
            "targetAudience": "教师",
            "estimatedMinutes": "25 minutes",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "style": {"style": "clean", "language": "zh-CN"},
            "pages": [
                {"id": "cover", "type": "cover", "title": "课程导入"},
                {"type": "wrap-up", "title": "总结", "bullets": "保持人工审核"},
            ],
        },
    }


def ppt_dsl_with_slide_map_drift():
    ppt = ppt_dsl_with_slide_shape_drift()
    ppt["spec"]["slides"] = {
        "cover": {
            "type": "cover",
            "title": {"text": "映射封面"},
            "subtitle": "对象映射转数组",
            "bullets": "保持 WAITING_REVIEW",
        },
        "recap": {
            "type": "conclusion",
            "title": "复盘",
            "bullets": ["Schema 校验", {"text": "人工审核"}],
        },
    }
    return ppt


class FakeResponses:
    def __init__(self, dsl):
        self.dsl = dsl
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "id": "resp_fake_real_demo_provider",
            "output_text": json.dumps(self.dsl, ensure_ascii=False),
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        }


class FakeClient:
    def __init__(self, dsl):
        self.responses = FakeResponses(dsl)


class FakeRawTextResponses:
    def __init__(self, output_text):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "id": "resp_fake_raw_real_demo_provider",
            "output_text": self.output_text,
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        }


class FakeRawTextClient:
    def __init__(self, output_text):
        self.responses = FakeRawTextResponses(output_text)


class FakeSequentialResponses:
    def __init__(self, dsls):
        self.dsls = list(dsls)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self.dsls) - 1)
        return {
            "id": f"resp_fake_real_demo_provider_{index + 1}",
            "output_text": json.dumps(self.dsls[index], ensure_ascii=False),
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        }


class FakeSequentialClient:
    def __init__(self, dsls):
        self.responses = FakeSequentialResponses(dsls)


class FakeNotFoundError(Exception):
    status_code = 404


class FakeBadRequestError(Exception):
    status_code = 400


class FakeAPIConnectionError(Exception):
    pass


class FakeChatCompletions:
    def __init__(self, dsl, *, fail_json_schema: bool = False, exc_type=None):
        self.dsl = dsl
        self.fail_json_schema = fail_json_schema
        self.exc_type = exc_type
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc_type is not None:
            raise self.exc_type("chat completions unavailable")
        if self.fail_json_schema and kwargs["response_format"]["type"] == "json_schema":
            raise FakeBadRequestError("json_schema unsupported")
        return {
            "id": "chatcmpl_fake_real_demo_provider",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(self.dsl, ensure_ascii=False),
                    }
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
        }


class FakeChat:
    def __init__(self, completions):
        self.completions = completions


class FakeResponsesNotFound:
    def __init__(self, exc_type=FakeNotFoundError):
        self.exc_type = exc_type
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        raise self.exc_type("responses unsupported")


class FakeChatFallbackClient:
    def __init__(
        self,
        dsl,
        *,
        fail_json_schema: bool = False,
        responses_exc_type=FakeNotFoundError,
        chat_exc_type=None,
    ):
        self.responses = FakeResponsesNotFound(responses_exc_type)
        self.chat = FakeChat(FakeChatCompletions(dsl, fail_json_schema=fail_json_schema, exc_type=chat_exc_type))


def matrix_input_payload(kind):
    if kind == "lab":
        return {
            "labGenerationContext": {
                "targetUsers": ["平台开发者"],
                "durationMinutes": 45,
                "difficulty": "beginner",
                "techTags": ["LLM"],
            }
        }
    if kind == "exam":
        return {"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}}
    if kind == "grading":
        return {"examDsl": valid_exam_dsl()}
    if kind == "ppt":
        return {"labDsl": {"kind": "Lab", "metadata": {"title": "真实 LLM Demo 实验"}}}
    return {}


def value_at_path(document, path):
    value = document
    for part in path:
        value = value[part]
    return value


REAL_LLM_SCHEMA_DRIFT_MATRIX = [
    {
        "id": "lab_materials_string_array",
        "kind": "lab",
        "factory": lab_dsl_with_materials_type_drift,
        "assertions": [
            (("spec", "materials", 0), {"type": "markdown", "path": "examples/input/demo-source.md"}),
            (("spec", "materials", 1), {"type": "markdown", "path": "实验讲义"}),
        ],
        "patches": ["set.spec.materials[0]", "set.spec.materials[1]"],
    },
    {
        "id": "lab_environment_resources_string",
        "kind": "lab",
        "factory": lab_dsl_with_environment_resources_type_drift,
        "assertions": [(("spec", "environment", "resources"), {"cpu": 2, "memoryGb": 4})],
        "patches": ["set.spec.environment.resources"],
    },
    {
        "id": "lab_environment_resources_aliases",
        "kind": "lab",
        "factory": lab_dsl_with_environment_resource_alias_drift,
        "assertions": [(("spec", "environment", "resources"), {"cpu": 3, "memoryGb": 8})],
        "patches": ["set.spec.environment.resources.cpu", "set.spec.environment.resources.memoryGb"],
    },
    {
        "id": "lab_grading_ref_shape_drift",
        "kind": "lab",
        "factory": lab_dsl_with_grading_ref_shape_drift,
        "assertions": [(("spec", "grading"), {"ref": "grading_real_demo_lab"})],
        "patches": ["set.spec.grading"],
    },
    {
        "id": "lab_materials_and_steps_object_map",
        "kind": "lab",
        "factory": lab_dsl_with_materials_and_steps_map_drift,
        "assertions": [
            (("spec", "materials", 0), {"type": "markdown", "path": "examples/input/demo-source.md"}),
            (("spec", "materials", 1), {"type": "markdown", "path": "guides/review.md"}),
            (("spec", "steps", 0, "id"), "step_review"),
            (("spec", "steps", 0, "instruction"), "确认 WAITING_REVIEW"),
            (("spec", "steps", 0, "commands"), ["python lab_cli.py review list"]),
            (("spec", "steps", 1, "id"), "step_record"),
            (("spec", "steps", 1, "instruction"), "记录审核结论"),
        ],
        "patches": ["set.spec.materials.from_object", "set.spec.steps.from_object"],
    },
    {
        "id": "lab_step_alias_fields",
        "kind": "lab",
        "factory": lab_dsl_with_step_alias_field_drift,
        "assertions": [
            (("spec", "steps", 0, "title"), "检查运行环境"),
            (("spec", "steps", 0, "instruction"), "确认 Python 与 pytest 可用。"),
            (("spec", "steps", 0, "commands"), ["python --version", "pytest --version"]),
            (("spec", "steps", 0, "expectedResult"), "输出版本号"),
            (("spec", "steps", 1, "id"), "step_alias_2"),
            (("spec", "steps", 1, "title"), "执行示例脚本"),
            (("spec", "steps", 1, "instruction"), "运行示例；记录 WAITING_REVIEW 输出"),
            (("spec", "steps", 1, "commands"), ["python main.py", "python -m pytest"]),
            (("spec", "steps", 1, "expectedResult"), "看到 WAITING_REVIEW；pytest passed"),
        ],
        "patches": [
            "set.spec.steps[0].title.from.name",
            "set.spec.steps[0].instruction.from.description",
            "set.spec.steps[0].commands.from.shellCommands",
            "set.spec.steps[0].expectedResult.from.expected",
            "set.spec.steps[1].id.from.stepId",
            "set.spec.steps[1].title.from.heading",
            "set.spec.steps[1].instruction.from.content",
            "set.spec.steps[1].commands.from.cmds",
            "set.spec.steps[1].expectedResult.from.successCriteria",
        ],
    },
    {
        "id": "exam_answer_and_grading_ref_object_fields",
        "kind": "exam",
        "factory": exam_dsl_with_question_string_field_drift,
        "assertions": [
            (("spec", "questions", 0, "answer"), "WAITING_REVIEW"),
            (("spec", "questions", 0, "gradingRef"), "check_q1"),
            (("spec", "questions", 1, "answer"), "步骤一；步骤二"),
            (("spec", "questions", 1, "gradingRef"), "check_q2"),
        ],
        "patches": [
            "set.spec.questions[0].answer",
            "set.spec.questions[0].gradingRef",
            "set.spec.questions[1].answer",
            "set.spec.questions[1].gradingRef",
        ],
    },
    {
        "id": "exam_missing_questions_custom_total_score",
        "kind": "exam",
        "factory": exam_dsl_without_questions_but_custom_total_score,
        "assertions": [
            (("spec", "totalScore"), 30),
            (("spec", "questions", 0, "score"), 30),
        ],
        "patches": ["set.spec.questions"],
    },
    {
        "id": "exam_top_level_questions",
        "kind": "exam",
        "factory": exam_dsl_with_top_level_questions,
        "assertions": [
            (("spec", "questions", 0, "title"), "顶层题目一"),
            (("spec", "questions", 1, "title"), "顶层题目二"),
            (("spec", "questions", 0, "score"), 60),
            (("spec", "questions", 1, "score"), 40),
        ],
        "patches": ["set.spec.questions.from.questions"],
    },
    {
        "id": "exam_questions_object_map",
        "kind": "exam",
        "factory": exam_dsl_with_question_map_drift,
        "assertions": [
            (("spec", "questions", 0, "id"), "q_review"),
            (("spec", "questions", 0, "title"), "说明审核边界"),
            (("spec", "questions", 0, "score"), 40),
            (("spec", "questions", 0, "gradingRef"), "check_review"),
            (("spec", "questions", 1, "id"), "q_import"),
            (("spec", "questions", 1, "score"), 60),
        ],
        "patches": [
            "set.spec.questions.from_object",
            "set.spec.questions[0].score",
            "set.spec.questions[0].gradingRef",
        ],
    },
    {
        "id": "exam_question_alias_fields",
        "kind": "exam",
        "factory": exam_dsl_with_question_alias_field_drift,
        "assertions": [
            (("spec", "questions", 0, "title"), "用 question 字段承载题目标题"),
            (("spec", "questions", 0, "stem"), "请补全 main.py，让程序输出 WAITING_REVIEW。"),
            (("spec", "questions", 0, "blankCode"), "print(____)"),
            (("spec", "questions", 0, "answer"), "WAITING_REVIEW"),
            (("spec", "questions", 0, "gradingRef"), "check_waiting_review"),
            (("spec", "questions", 1, "stem"), "运行 pytest；确认所有用例通过"),
            (("spec", "questions", 1, "answer"), "pytest；passed"),
            (("spec", "questions", 1, "gradingRef"), "check_pytest_passed"),
        ],
        "patches": [
            "set.spec.questions[0].title.from.name",
            "set.spec.questions[0].stem.from.question",
            "set.spec.questions[0].blankCode.from.starterCode",
            "set.spec.questions[0].answer.from.correctAnswer",
            "set.spec.questions[0].gradingRef.from.checkId",
            "set.spec.questions[1].stem.from.prompt",
        ],
    },
    {
        "id": "grading_required_limits_non_string_values",
        "kind": "grading",
        "factory": grading_dsl_with_required_limits_type_drift,
        "assertions": [
            (("spec", "assessmentPlan", 0, "executionPlan", "requiredLimits", "cpu"), "required"),
            (("spec", "assessmentPlan", 0, "executionPlan", "requiredLimits", "memory"), "required"),
            (("spec", "assessmentPlan", 0, "executionPlan", "requiredLimits", "timeout"), "30s"),
        ],
        "patches": [
            "set.spec.assessmentPlan[0].executionPlan.requiredLimits.cpu",
            "set.spec.assessmentPlan[0].executionPlan.requiredLimits.memory",
            "set.spec.assessmentPlan[0].executionPlan.requiredLimits.timeout",
        ],
    },
    {
        "id": "grading_metadata_object_fields",
        "kind": "grading",
        "factory": grading_dsl_with_metadata_string_field_drift,
        "assertions": [
            (("metadata", "id"), "grading-real-demo-provider-test"),
            (("metadata", "title"), "真实 LLM Demo Provider 测试评分"),
            (("metadata", "sourceExamId"), "exam-real-demo-provider-test"),
        ],
        "patches": ["set.metadata.id", "set.metadata.title", "set.metadata.sourceExamId"],
    },
    {
        "id": "grading_check_string_fields",
        "kind": "grading",
        "factory": grading_dsl_with_check_string_field_drift,
        "assertions": [
            (("spec", "checks", 0, "id"), "check_stdout"),
            (("spec", "checks", 0, "command"), "python main.py"),
            (("spec", "checks", 1, "id"), "2"),
            (("spec", "checks", 1, "path"), "result.csv"),
            (("spec", "checks", 2, "id"), "check_json"),
            (("spec", "checks", 2, "path"), "metrics.json"),
            (("spec", "checks", 2, "jsonPath"), "$.score"),
        ],
        "patches": [
            "set.spec.checks[0].id",
            "set.spec.checks[0].command",
            "set.spec.checks[1].id",
            "set.spec.checks[1].path",
            "set.spec.checks[2].id",
            "set.spec.checks[2].path",
            "set.spec.checks[2].jsonPath",
        ],
    },
    {
        "id": "grading_check_alias_fields",
        "kind": "grading",
        "factory": grading_dsl_with_check_alias_field_drift,
        "assertions": [
            (("spec", "checks", 0, "id"), "check_stdout_alias"),
            (("spec", "checks", 0, "type"), "stdout_contains"),
            (("spec", "checks", 0, "command"), "python main.py"),
            (("spec", "checks", 0, "expected"), ["WAITING_REVIEW", "PASS"]),
            (("spec", "checks", 0, "score"), 50),
            (("spec", "checks", 1, "id"), "check_file_alias"),
            (("spec", "checks", 1, "type"), "file_exists"),
            (("spec", "checks", 1, "path"), "result.csv"),
            (("spec", "checks", 1, "score"), 25),
            (("spec", "checks", 2, "id"), "check_json_alias"),
            (("spec", "checks", 2, "type"), "json_field"),
            (("spec", "checks", 2, "path"), "metrics.json"),
            (("spec", "checks", 2, "jsonPath"), "$.score"),
            (("spec", "checks", 2, "expectedValue"), 0.9),
            (("spec", "checks", 2, "score"), 25),
        ],
        "patches": [
            "set.spec.checks[0].id.from.checkId",
            "set.spec.checks[0].type.from.checkType",
            "set.spec.checks[0].type",
            "set.spec.checks[0].command.from.cmd",
            "set.spec.checks[0].expected.from.expectedOutput",
            "set.spec.checks[0].expected",
            "set.spec.checks[0].score.from.points",
            "set.spec.checks[1].id.from.ruleId",
            "set.spec.checks[1].type.from.kind",
            "set.spec.checks[1].type",
            "set.spec.checks[1].path.from.filePath",
            "set.spec.checks[1].path",
            "set.spec.checks[1].score.from.points",
            "set.spec.checks[2].id.from.name",
            "set.spec.checks[2].type.from.runner",
            "set.spec.checks[2].type",
            "set.spec.checks[2].path.from.filePath",
            "set.spec.checks[2].jsonPath.from.fieldPath",
            "set.spec.checks[2].expectedValue.from.expectedJsonValue",
            "set.spec.checks[2].score.from.weight",
        ],
    },
    {
        "id": "grading_assessment_plan_input_summary",
        "kind": "grading",
        "factory": grading_dsl_with_assessment_plan_input_summary_drift,
        "assertions": [
            (("spec", "assessmentPlan", 0, "inputSummary"), "检查命令输出包含 WAITING_REVIEW"),
            (("spec", "assessmentPlan", 1, "inputSummary"), "Plan pytest check at tests/test_main.py"),
        ],
        "patches": [
            "set.spec.assessmentPlan[0].inputSummary",
            "set.spec.assessmentPlan[1].inputSummary",
        ],
    },
    {
        "id": "grading_assessment_plan_alias_fields",
        "kind": "grading",
        "factory": grading_dsl_with_assessment_plan_alias_field_drift,
        "assertions": [
            (("spec", "assessmentPlan", 0, "checkId"), "check_stdout"),
            (("spec", "assessmentPlan", 0, "type"), "stdout_contains"),
            (("spec", "assessmentPlan", 0, "runner"), "StdoutContainsGrader"),
            (("spec", "assessmentPlan", 0, "inputSummary"), "检查命令输出包含 WAITING_REVIEW"),
            (("spec", "assessmentPlan", 0, "executionPlan", "requiredLimits", "network"), "disabled_by_default"),
            (("spec", "assessmentPlan", 1, "checkId"), "check_pytest"),
            (("spec", "assessmentPlan", 1, "type"), "pytest"),
            (("spec", "assessmentPlan", 1, "runner"), "PytestGrader"),
            (("spec", "assessmentPlan", 1, "inputSummary"), "运行 pytest 校验答案"),
            (("spec", "assessmentPlan", 1, "executionPlan", "strategy"), "MOCK_PLAN_ONLY"),
            (("spec", "assessmentPlan", 1, "executionPlan", "requiredLimits", "cpu"), "required"),
            (("spec", "assessmentPlan", 1, "executionPlan", "requiredLimits", "timeout"), "30s"),
            (("spec", "assessmentPlan", 1, "mockEvidence"), {"status": "MOCK_EVIDENCE_NOT_COLLECTED"}),
            (("spec", "assessmentPlan", 1, "riskLevel"), "medium"),
            (("spec", "assessmentPlan", 1, "sandboxRequiredBeforeRealExecution"), True),
        ],
        "patches": [
            "set.spec.assessmentPlan[0].checkId.from.check_id",
            "set.spec.assessmentPlan[0].inputSummary.from.summary",
            "set.spec.assessmentPlan[0].executionPlan.from.execution",
            "set.spec.assessmentPlan[0].executionPlan.requiredLimits.from.limits",
            "set.spec.assessmentPlan[0].mockEvidence.from.evidence",
            "set.spec.assessmentPlan[0].riskLevel.from.risk",
            "set.spec.assessmentPlan[0].sandboxRequiredBeforeRealExecution.from.sandboxRequired",
            "set.spec.assessmentPlan[1].checkId.from.check_id",
            "set.spec.assessmentPlan[1].inputSummary.from.summary",
            "set.spec.assessmentPlan[1].executionPlan.from.runPlan",
            "set.spec.assessmentPlan[1].executionPlan.requiredLimits.from.limits",
        ],
    },
    {
        "id": "grading_assessment_plan_mock_evidence",
        "kind": "grading",
        "factory": grading_dsl_with_assessment_plan_mock_evidence_drift,
        "assertions": [
            (("spec", "assessmentPlan", 0, "mockEvidence"), {"status": "MOCK_EVIDENCE_NOT_COLLECTED"}),
            (("spec", "assessmentPlan", 1, "mockEvidence"), {"status": "MOCK_EVIDENCE_NOT_COLLECTED"}),
        ],
        "patches": [
            "set.spec.assessmentPlan[0].mockEvidence.status",
            "set.spec.assessmentPlan[1].mockEvidence.status",
        ],
    },
    {
        "id": "grading_checks_and_assessment_plan_object_map",
        "kind": "grading",
        "factory": grading_dsl_with_check_and_assessment_plan_map_drift,
        "assertions": [
            (("spec", "checks", 0, "id"), "check_review"),
            (("spec", "checks", 0, "type"), "stdout_contains"),
            (("spec", "checks", 0, "command"), "python main.py"),
            (("spec", "checks", 0, "expected"), ["WAITING_REVIEW"]),
            (("spec", "checks", 1, "id"), "check_pytest"),
            (("spec", "checks", 1, "type"), "pytest"),
            (("spec", "checks", 1, "path"), "tests/test_main.py"),
            (("spec", "assessmentPlan", 0, "checkId"), "check_review"),
            (("spec", "assessmentPlan", 0, "executionPlan", "requiredLimits", "cpu"), "required"),
            (("spec", "assessmentPlan", 0, "executionPlan", "requiredLimits", "timeout"), "30s"),
            (("spec", "assessmentPlan", 1, "checkId"), "check_pytest"),
        ],
        "patches": [
            "set.spec.checks.from_object",
            "set.spec.assessmentPlan.from_object",
            "set.spec.checks[0].type",
            "set.spec.checks[0].command",
            "set.spec.checks[0].expected",
            "set.spec.checks[1].type",
            "set.spec.checks[1].path",
            "set.spec.assessmentPlan[0].executionPlan.requiredLimits.cpu",
            "set.spec.assessmentPlan[0].executionPlan.requiredLimits.timeout",
        ],
    },
    {
        "id": "ppt_metadata_and_slide_named_fields",
        "kind": "ppt",
        "factory": ppt_dsl_with_named_string_field_drift,
        "assertions": [
            (("metadata", "title"), "PPT 标题字段对象"),
            (("metadata", "audience"), "教师"),
            (("spec", "slides", 0, "title"), "封面标题字段对象"),
            (("spec", "slides", 0, "subtitle"), "副标题字段对象"),
        ],
        "patches": [
            "set.metadata.title",
            "set.metadata.audience",
            "set.spec.slides[0].title",
            "set.spec.slides[0].subtitle",
        ],
    },
    {
        "id": "ppt_slide_alias_fields",
        "kind": "ppt",
        "factory": ppt_dsl_with_slide_alias_field_drift,
        "assertions": [
            (("spec", "slides", 0, "id"), "goals"),
            (("spec", "slides", 0, "type"), "content"),
            (("spec", "slides", 0, "title"), "学习目标"),
            (
                ("spec", "slides", 0, "bullets"),
                ["理解真实 LLM 产物校验", "保持 WAITING_REVIEW", "讲稿提示：只做人工审核前预览。"],
            ),
            (("spec", "slides", 1, "id"), "recap"),
            (("spec", "slides", 1, "type"), "summary"),
            (("spec", "slides", 1, "title"), "总结与下一步"),
            (("spec", "slides", 1, "bullets"), ["复盘 Schema 漂移", "记录下一步建议"]),
        ],
        "patches": [
            "set.spec.slides[0].id.from.slideId",
            "set.spec.slides[0].type.from.layout",
            "set.spec.slides[0].type",
            "set.spec.slides[0].title.from.heading",
            "set.spec.slides[0].bullets.from.points",
            "set.spec.slides[0].bullets",
            "set.spec.slides[1].id.from.key",
            "set.spec.slides[1].type.from.kind",
            "set.spec.slides[1].type",
            "set.spec.slides[1].title.from.name",
            "set.spec.slides[1].bullets.from.items",
            "set.spec.slides[1].bullets",
        ],
    },
    {
        "id": "ppt_slides_object_map",
        "kind": "ppt",
        "factory": ppt_dsl_with_slide_map_drift,
        "assertions": [
            (("spec", "slides", 0, "id"), "cover"),
            (("spec", "slides", 0, "type"), "title"),
            (("spec", "slides", 0, "title"), "映射封面"),
            (("spec", "slides", 0, "bullets"), ["保持 WAITING_REVIEW"]),
            (("spec", "slides", 1, "id"), "recap"),
            (("spec", "slides", 1, "type"), "summary"),
            (("spec", "slides", 1, "bullets"), ["Schema 校验", "人工审核"]),
        ],
        "patches": [
            "set.spec.slides.from_object",
            "set.spec.slides[0].type",
            "set.spec.slides[0].title",
            "set.spec.slides[0].bullets",
            "set.spec.slides[1].type",
            "set.spec.slides[1].bullets",
        ],
    },
]


def test_real_llm_demo_schema_drift_matrix_regression(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    for sample in REAL_LLM_SCHEMA_DRIFT_MATRIX:
        fake_client = FakeClient(sample["factory"]())
        result = run_real_llm_demo_dsl_generation(
            RealLlmDemoDslRequest(
                kind=sample["kind"],
                input_ref="examples/input/demo-source.md",
                input_payload=matrix_input_payload(sample["kind"]),
                model="test-model",
                explicit_real_call_opt_in=True,
                confirm_waiting_review=True,
                confirm_no_auto_publish=True,
            ),
            root=ROOT,
            client_factory=lambda **_: fake_client,
        )

        assert result["schemaValidated"] is True, sample["id"]
        assert result["generatedStatus"] == "WAITING_REVIEW", sample["id"]
        assert result["reviewRequired"] is True, sample["id"]
        assert result["normalization"]["applied"] is True, sample["id"]
        for path, expected in sample["assertions"]:
            assert value_at_path(result["dsl"], path) == expected, sample["id"]
        for patch in sample["patches"]:
            assert patch in result["normalization"]["patches"], sample["id"]


@pytest.mark.real_llm_online
def test_real_llm_demo_online_smoke_lab_schema_when_enabled():
    if os.environ.get(ONLINE_SMOKE_ENV) != "1":
        pytest.skip(f"set {ONLINE_SMOKE_ENV}=1 to run optional real LLM online smoke")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("set OPENAI_API_KEY to run optional real LLM online smoke")

    model = os.environ.get(ONLINE_SMOKE_MODEL_ENV) or os.environ.get("OPENAI_MODEL")
    if not model:
        pytest.skip(f"set {ONLINE_SMOKE_MODEL_ENV} or OPENAI_MODEL to run optional real LLM online smoke")

    max_output_tokens = _read_positive_int_env(ONLINE_SMOKE_MAX_OUTPUT_TOKENS_ENV, default=1200)
    timeout_seconds = _read_positive_int_env(ONLINE_SMOKE_TIMEOUT_ENV, default=60)

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "onlineSmoke": {
                    "purpose": "schema-only optional real LLM smoke",
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 30,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                    "requirements": [
                        "只生成 Lab DSL JSON",
                        "status 必须为 WAITING_REVIEW",
                        "不得声明真实云资源已创建或发布完成",
                    ],
                }
            },
            model=model,
            base_url=os.environ.get(ONLINE_SMOKE_BASE_URL_ENV) or os.environ.get("OPENAI_BASE_URL"),
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
            repair_on_schema_failure=True,
            api_surface=os.environ.get(ONLINE_SMOKE_API_SURFACE_ENV, "chat.completions"),
            trace_id="trace_real_llm_online_smoke_lab",
        ),
        root=ROOT,
    )

    assert result["kind"] == "lab"
    assert result["outputKind"] == "Lab"
    assert result["realLlmCalled"] is True
    assert result["networkAccess"] is True
    assert result["schemaValidated"] is True
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["reviewRequired"] is True
    assert result["reviewBypassed"] is False
    assert result["autoPublishAllowed"] is False
    assert result["realPublish"] is False
    assert result["secretValueReturned"] is False
    assert result["dsl"]["kind"] == "Lab"
    assert result["dsl"]["status"] == "WAITING_REVIEW"
    assert result["requestCount"] in {1, 2}
    assert result["apiSurface"]

    serialized = json.dumps(result, ensure_ascii=False)
    secret = os.environ.get("OPENAI_API_KEY", "")
    if secret and secret in serialized:
        raise AssertionError("real LLM online smoke result leaked OPENAI_API_KEY")


def _read_positive_int_env(name: str, *, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise AssertionError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise AssertionError(f"{name} must be greater than 0")
    return parsed


def test_real_llm_demo_dsl_generation_uses_injected_client_and_validates_schema(monkeypatch):
    fake_client = FakeClient(valid_exam_dsl())
    created_kwargs = []

    def client_factory(**kwargs):
        created_kwargs.append(kwargs)
        return fake_client

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_ref="examples/input/demo-source.md",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            base_url="https://example.test/v1",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
            trace_id="trace_real_demo_provider",
        ),
        root=ROOT,
        client_factory=client_factory,
    )

    assert created_kwargs == [{"api_key": "sk-test-redacted", "base_url": "https://example.test/v1"}]
    assert len(fake_client.responses.calls) == 1
    call = fake_client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["temperature"] == 0
    assert call["stream"] is False
    assert result["mode"] == "REAL_LLM_DEMO_DSL_GENERATION"
    assert result["kind"] == "exam"
    assert result["outputKind"] == "Exam"
    assert result["realLlmCalled"] is True
    assert result["schemaValidated"] is True
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["secretValueReturned"] is False
    assert result["baseUrlConfigured"] is True
    assert result["baseUrlSource"] == "argument"
    assert "https://example.test/v1" not in json.dumps(result, ensure_ascii=False)
    assert result["responseId"] == "resp_fake_real_demo_provider"
    assert result["usage"]["total_tokens"] == 30
    assert result["dsl"]["metadata"]["id"] == "exam-real-demo-provider-test"
    assert result["apiSurface"] == "responses"


def test_real_llm_demo_dsl_generation_falls_back_to_chat_completions(monkeypatch):
    fake_client = FakeChatFallbackClient(valid_exam_dsl())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_ref="examples/input/demo-source.md",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
            trace_id="trace_real_demo_provider",
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert len(fake_client.responses.calls) == 1
    assert len(fake_client.chat.completions.calls) == 1
    call = fake_client.chat.completions.calls[0]
    assert call["messages"][0]["role"] == "system"
    assert call["response_format"]["type"] == "json_schema"
    assert call["response_format"]["json_schema"]["name"] == "exam_dsl"
    assert result["apiSurface"] == "chat.completions"
    assert result["responseId"] == "chatcmpl_fake_real_demo_provider"
    assert result["usage"]["total_tokens"] == 33


def test_real_llm_demo_dsl_generation_falls_back_to_chat_on_responses_connection_error(monkeypatch):
    fake_client = FakeChatFallbackClient(valid_exam_dsl(), responses_exc_type=FakeAPIConnectionError)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert len(fake_client.responses.calls) == 1
    assert len(fake_client.chat.completions.calls) == 1
    assert result["apiSurface"] == "chat.completions"
    assert result["schemaValidated"] is True


def test_real_llm_demo_dsl_generation_can_force_chat_completions(monkeypatch):
    fake_client = FakeChatFallbackClient(valid_exam_dsl())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
            api_surface="chat.completions",
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert len(fake_client.responses.calls) == 0
    assert len(fake_client.chat.completions.calls) == 1
    assert result["apiSurface"] == "chat.completions"
    assert result["schemaValidated"] is True


def test_real_llm_demo_dsl_call_failure_reports_api_surface_attempts(monkeypatch):
    fake_client = FakeChatFallbackClient(
        valid_exam_dsl(),
        responses_exc_type=FakeAPIConnectionError,
        chat_exc_type=FakeAPIConnectionError,
    )

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    try:
        run_real_llm_demo_dsl_generation(
            RealLlmDemoDslRequest(
                kind="exam",
                input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
                model="test-model",
                explicit_real_call_opt_in=True,
                confirm_waiting_review=True,
                confirm_no_auto_publish=True,
            ),
            root=ROOT,
            client_factory=lambda **_: fake_client,
        )
    except ProviderError as exc:
        assert exc.code == "REAL_LLM_DEMO_DSL_CALL_FAILED"
        error = exc.errors[0]
        assert error["apiSurface"] == "responses,chat.completions"
        attempts = json.loads(error["attempts"])
        assert attempts == [
            {"apiSurface": "responses", "errorType": "FakeAPIConnectionError"},
            {"apiSurface": "chat.completions", "errorType": "FakeAPIConnectionError"},
        ]
    else:
        raise AssertionError("expected ProviderError")


def test_real_llm_demo_dsl_generation_falls_back_to_chat_json_object(monkeypatch):
    fake_client = FakeChatFallbackClient(valid_exam_dsl(), fail_json_schema=True)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"source": "demo"},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert [call["response_format"]["type"] for call in fake_client.chat.completions.calls] == [
        "json_schema",
        "json_object",
    ]
    assert result["apiSurface"] == "chat.completions.json_object"
    assert result["schemaValidated"] is True


def test_real_llm_demo_dsl_generation_unwraps_common_response_envelope(monkeypatch):
    fake_client = FakeClient({"data": {"labDsl": lab_dsl_with_shape_drift()}})

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={"labGenerationContext": {"durationMinutes": 45}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert result["schemaValidated"] is True
    assert result["dsl"]["kind"] == "Lab"
    assert result["dsl"]["metadata"]["id"] == "lab-real-demo-provider-test"
    assert "unwrap.response.data.labDsl" in result["normalization"]["patches"]


def test_real_llm_demo_dsl_generation_accepts_single_item_array_root(monkeypatch):
    fake_client = FakeClient([valid_exam_dsl()])

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert result["schemaValidated"] is True
    assert result["dsl"]["kind"] == "Exam"
    assert result["dsl"]["metadata"]["id"] == "exam-real-demo-provider-test"


def test_real_llm_demo_dsl_generation_extracts_markdown_fenced_json(monkeypatch):
    fenced_output = (
        "下面是生成的 DSL：\n"
        "```json\n"
        f"{json.dumps(valid_exam_dsl(), ensure_ascii=False)}\n"
        "```\n"
        "请进入人工审核。"
    )
    fake_client = FakeRawTextClient(fenced_output)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert result["schemaValidated"] is True
    assert result["dsl"]["kind"] == "Exam"
    assert result["responseId"] == "resp_fake_raw_real_demo_provider"


def test_real_llm_demo_dsl_generation_normalizes_schema_shape(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_shape_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "labGenerationContext": {
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 45,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert result["schemaValidated"] is True
    assert result["normalization"]["applied"] is True
    assert "remove.$.metadata.description" in result["normalization"]["patches"]
    assert "remove.$.metadata.targetUsers" in result["normalization"]["patches"]
    assert result["dsl"]["metadata"]["category"] == "ai-platform"
    assert result["dsl"]["spec"]["environment"]["type"] == "notebook"
    assert result["dsl"]["spec"]["environment"]["image"] == "python:3.11"
    assert result["dsl"]["spec"]["steps"][0]["id"] == "step_1"


def test_real_llm_demo_lab_promotes_top_level_aliases(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_top_level_aliases())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={"labGenerationContext": {"durationMinutes": 45}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    lab = result["dsl"]
    patches = result["normalization"]["patches"]
    assert result["schemaValidated"] is True
    assert lab["metadata"]["difficulty"] == "intermediate"
    assert lab["metadata"]["durationMinutes"] == 50
    assert lab["metadata"]["tags"] == ["Python", "Notebook"]
    assert lab["spec"]["objectives"] == ["理解字段别名归一化"]
    assert lab["spec"]["targetUsers"] == ["教师", "学生"]
    assert lab["spec"]["environment"]["resources"] == {"cpu": 2, "memoryGb": 4}
    assert lab["spec"]["steps"][0]["title"] == "完成实验步骤"
    assert "set.spec.from_top_level_aliases" in patches
    assert "set.metadata.difficulty.from.level" in patches


def test_real_llm_demo_lab_normalizes_metadata_and_list_drift(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_metadata_and_list_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "labGenerationContext": {
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 45,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    lab = result["dsl"]
    assert result["schemaValidated"] is True
    assert lab["metadata"]["id"] == "lab-real-demo-provider-test"
    assert lab["metadata"]["title"] == "真实 LLM Demo Provider 测试实验"
    assert lab["metadata"]["category"] == "AI；实训"
    assert lab["metadata"]["difficulty"] == "beginner"
    assert lab["metadata"]["durationMinutes"] == 45
    assert lab["metadata"]["tags"] == ["LLM", "Python", "Notebook"]
    assert lab["spec"]["objectives"] == ["理解 WAITING_REVIEW", "完成人工审核"]
    assert lab["spec"]["targetUsers"] == ["教师", "学生", "平台开发者"]
    assert "set.metadata.id" in result["normalization"]["patches"]
    assert "set.metadata.category" in result["normalization"]["patches"]
    assert "set.metadata.difficulty" in result["normalization"]["patches"]
    assert "set.metadata.durationMinutes" in result["normalization"]["patches"]
    assert "set.metadata.tags" in result["normalization"]["patches"]
    assert "set.spec.objectives" in result["normalization"]["patches"]
    assert "set.spec.targetUsers" in result["normalization"]["patches"]


def test_real_llm_demo_lab_normalizes_materials_type_drift(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_materials_type_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "labGenerationContext": {
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 45,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    materials = result["dsl"]["spec"]["materials"]
    assert result["schemaValidated"] is True
    assert materials == [
        {"type": "markdown", "path": "examples/input/demo-source.md"},
        {"type": "markdown", "path": "实验讲义"},
    ]
    assert "set.spec.materials[0]" in result["normalization"]["patches"]
    assert "set.spec.materials[1]" in result["normalization"]["patches"]


def test_real_llm_demo_lab_normalizes_environment_resources_type_drift(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_environment_resources_type_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "labGenerationContext": {
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 45,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert result["schemaValidated"] is True
    assert result["dsl"]["spec"]["environment"]["resources"] == {"cpu": 2, "memoryGb": 4}
    assert "set.spec.environment.resources" in result["normalization"]["patches"]


def test_real_llm_demo_lab_parses_environment_resource_text_drift(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_parseable_resource_text_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "labGenerationContext": {
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 45,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert result["schemaValidated"] is True
    assert result["dsl"]["spec"]["environment"]["resources"] == {"cpu": 3, "memoryGb": 6}
    assert "set.spec.environment.resources" in result["normalization"]["patches"]


def test_real_llm_demo_lab_normalizes_environment_resource_value_drift(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_environment_resource_value_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "labGenerationContext": {
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 45,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert result["schemaValidated"] is True
    assert result["dsl"]["spec"]["environment"]["resources"] == {"cpu": 2, "memoryGb": 4}
    assert "set.spec.environment.resources.cpu" in result["normalization"]["patches"]
    assert "set.spec.environment.resources.memoryGb" in result["normalization"]["patches"]
    assert "remove.$.spec.environment.resources.gpu" not in result["normalization"]["patches"]


def test_real_llm_demo_lab_normalizes_environment_resource_alias_drift(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_environment_resource_alias_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "labGenerationContext": {
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 45,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert result["schemaValidated"] is True
    assert result["dsl"]["spec"]["environment"]["resources"] == {"cpu": 3, "memoryGb": 8}
    assert "set.spec.environment.resources.cpu" in result["normalization"]["patches"]
    assert "set.spec.environment.resources.memoryGb" in result["normalization"]["patches"]


def test_real_llm_demo_lab_normalizes_rich_materials_and_step_drift(monkeypatch):
    fake_client = FakeClient(lab_dsl_with_rich_materials_and_step_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="lab",
            input_ref="examples/input/demo-source.md",
            input_payload={
                "labGenerationContext": {
                    "targetUsers": ["平台开发者"],
                    "durationMinutes": 45,
                    "difficulty": "beginner",
                    "techTags": ["LLM"],
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    lab = result["dsl"]
    assert result["schemaValidated"] is True
    assert lab["spec"]["materials"] == [
        {"type": "markdown", "path": "examples/input/demo-source.md"},
        {"type": "pdf", "path": "课程讲义.pdf"},
    ]
    assert lab["spec"]["steps"][0] == {
        "id": "1",
        "title": "环境检查",
        "instruction": "检查 Python；记录版本",
        "commands": ["python --version", "pip --version"],
        "expectedResult": "输出版本号",
    }
    assert "set.spec.materials[0]" in result["normalization"]["patches"]
    assert "set.spec.materials[1]" in result["normalization"]["patches"]
    assert "set.spec.steps[0].id" in result["normalization"]["patches"]
    assert "set.spec.steps[0].instruction" in result["normalization"]["patches"]
    assert "set.spec.steps[0].commands" in result["normalization"]["patches"]


def test_real_llm_demo_exam_normalizes_question_string_field_drift(monkeypatch):
    fake_client = FakeClient(exam_dsl_with_question_string_field_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    questions = result["dsl"]["spec"]["questions"]
    assert result["schemaValidated"] is True
    assert all(isinstance(question["answer"], str) for question in questions)
    assert all(isinstance(question["gradingRef"], str) for question in questions)
    assert questions[0]["answer"] == "WAITING_REVIEW"
    assert questions[0]["gradingRef"] == "check_q1"
    assert questions[1]["answer"] == "步骤一；步骤二"
    assert questions[1]["gradingRef"] == "check_q2"
    assert questions[2]["answer"] == "42"
    assert questions[2]["gradingRef"] == "check_q3"
    assert "set.spec.questions[0].answer" in result["normalization"]["patches"]
    assert "set.spec.questions[0].gradingRef" in result["normalization"]["patches"]
    assert "set.spec.questions[3].answer" in result["normalization"]["patches"]


def test_real_llm_demo_exam_moves_answer_like_grading_refs_to_answer(monkeypatch):
    fake_client = FakeClient(exam_dsl_with_answer_like_grading_refs())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    questions = result["dsl"]["spec"]["questions"]
    patches = result["normalization"]["patches"]
    assert result["schemaValidated"] is True
    assert [question["gradingRef"] for question in questions] == ["q1", "q2", "q3", "q4"]
    assert questions[0]["answer"] == "方法一：查看扩展图标；方法二：观察状态栏图标。"
    assert questions[1]["answer"].startswith("def greet")
    assert questions[2]["answer"] == "'Hello'"
    assert questions[3]["answer"] == "已有答案应优先保留"
    assert "set.spec.questions[0].answer.fromUnstableGradingRef" in patches
    assert "set.spec.questions[0].gradingRef.fromUnstableValue" in patches
    assert "set.spec.questions[1].answer.fromUnstableGradingRef" in patches
    assert "set.spec.questions[2].gradingRef.fromUnstableValue" in patches
    assert "set.spec.questions[3].answer.fromUnstableGradingRef" not in patches
    assert "set.spec.questions[3].gradingRef.fromUnstableValue" in patches


def test_real_llm_demo_exam_normalizes_generic_manual_grading_refs(monkeypatch):
    fake_client = FakeClient(exam_dsl_with_generic_manual_grading_refs())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    questions = result["dsl"]["spec"]["questions"]
    patches = result["normalization"]["patches"]
    assert result["schemaValidated"] is True
    assert [question["gradingRef"] for question in questions] == ["q1", "q2", "q3", "q4"]
    assert [question.get("answer", "") for question in questions] == ["", "", "", ""]
    assert "set.spec.questions[0].answer.fromUnstableGradingRef" not in patches
    assert "set.spec.questions[0].gradingRef.fromUnstableValue" in patches
    assert "set.spec.questions[3].gradingRef.fromUnstableValue" in patches


def test_real_llm_demo_exam_promotes_spec_aliases(monkeypatch):
    fake_client = FakeClient(exam_dsl_with_spec_aliases())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-alias-demo"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    exam = result["dsl"]
    patches = result["normalization"]["patches"]
    assert result["schemaValidated"] is True
    assert exam["metadata"]["sourceLabId"] == "lab-alias-demo"
    assert exam["metadata"]["difficulty"] == "intermediate"
    assert exam["spec"]["questionType"] == "short_answer"
    assert exam["spec"]["totalScore"] == 100
    assert [question["score"] for question in exam["spec"]["questions"]] == [50, 50]
    assert exam["spec"]["questions"][0]["gradingRef"] == "check_review_boundary"
    assert "set.metadata.sourceLabId.from.labId" in patches
    assert "set.spec.questionType.from.type" in patches
    assert "set.spec.questions.from.items" in patches


def test_real_llm_demo_exam_normalizes_question_type_and_score_drift(monkeypatch):
    fake_client = FakeClient(exam_dsl_with_question_type_and_score_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"id": "lab-real-demo-provider-test"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    exam = result["dsl"]
    questions = exam["spec"]["questions"]
    assert result["schemaValidated"] is True
    assert exam["spec"]["questionType"] == "coding_task"
    assert exam["spec"]["totalScore"] == 100
    assert [question["score"] for question in questions] == [34, 33, 33]
    assert sum(question["score"] for question in questions) == exam["spec"]["totalScore"]
    assert "set.spec.questionType" in result["normalization"]["patches"]
    assert "set.spec.totalScore" in result["normalization"]["patches"]
    assert "set.spec.questions[0].score" in result["normalization"]["patches"]
    assert "set.spec.questions[1].score" in result["normalization"]["patches"]
    assert "set.spec.questions[2].score" in result["normalization"]["patches"]


def test_real_llm_demo_schema_failure_does_not_retry_by_default(monkeypatch):
    invalid_exam = valid_exam_dsl()
    invalid_exam["metadata"].pop("sourceLabId")
    invalid_exam["spec"]["questions"][0]["stem"] = "SECRET_STEM_SHOULD_NOT_LEAK"
    invalid_exam["spec"]["questions"][0]["answer"] = None
    fake_client = FakeSequentialClient([invalid_exam, valid_exam_dsl()])
    request = RealLlmDemoDslRequest(
        kind="exam",
        input_ref="examples/input/demo-source.md",
        input_payload={},
        model="test-model",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
    )

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    try:
        run_real_llm_demo_dsl_generation(request, root=ROOT, client_factory=lambda **_: fake_client)
    except ProviderError as exc:
        assert exc.code == "REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED"
        fields = {error["field"] for error in exc.errors}
        assert "$.metadata.sourceLabId" in fields
        assert "$.spec.questions[0].answer" in fields
        assert len(fake_client.responses.calls) == 1
        diagnostic = exc.details["schemaFailureDiagnostic"]
        assert diagnostic["kind"] == "exam"
        assert diagnostic["outputKind"] == "Exam"
        assert diagnostic["errorTotal"] == 2
        assert "expected_string" in diagnostic["suspectedDriftTypes"]
        assert diagnostic["documentShape"]["counts"]["questions"] == 1
        sensitive_error = next(error for error in diagnostic["errors"] if error["field"] == "$.spec.questions[0].answer")
        assert sensitive_error["sensitiveValueRedacted"] is True
        diagnostic_text = json.dumps(diagnostic, ensure_ascii=False)
        assert "SECRET_STEM_SHOULD_NOT_LEAK" not in diagnostic_text
        assert "sk-test-redacted" not in diagnostic_text
        context = build_real_llm_demo_dsl_error_context(exc, request=request, root=ROOT)
        assert context["schemaFailureDiagnostic"] == diagnostic
    else:
        raise AssertionError("expected ProviderError")


def test_schema_failure_diagnostic_classifies_standard_validator_constraints():
    errors = [
        {"field": "$.name", "reason": "expected length >= 3"},
        {"field": "$.code", "reason": "expected string matching pattern '^[A-Z]+$'"},
        {"field": "$.score", "reason": "expected <= 100"},
        {"field": "$.choice", "reason": "expected exactly one schema in oneOf to match"},
    ]

    diagnostic = build_real_llm_schema_failure_diagnostic(
        errors,
        document={"kind": "Exam", "metadata": {}, "spec": {}},
        kind="exam",
        output_kind="Exam",
    )

    assert diagnostic["suspectedDriftTypes"] == [
        "composition_mismatch",
        "numeric_range",
        "pattern_mismatch",
        "string_length",
    ]
    assert len(diagnostic["recommendedActions"]) == 4


def test_real_llm_demo_schema_failure_can_repair_once(monkeypatch):
    invalid_exam = valid_exam_dsl()
    invalid_exam["metadata"].pop("sourceLabId")
    repaired_exam = valid_exam_dsl()
    repaired_exam["metadata"]["id"] = "exam-real-demo-provider-repaired"
    repaired_exam["metadata"]["sourceLabId"] = "lab-real-demo-provider-repaired"
    fake_client = FakeSequentialClient([invalid_exam, repaired_exam])

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="exam",
            input_ref="examples/input/demo-source.md",
            input_payload={},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
            repair_on_schema_failure=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    assert len(fake_client.responses.calls) == 2
    repair_input = fake_client.responses.calls[1]["input"]
    assert "SCHEMA_VALIDATION_REPAIR_ONCE" in repair_input
    assert "Failed JSON response" in repair_input
    assert result["schemaValidated"] is True
    assert result["requestCount"] == 2
    assert result["singleRequestForKind"] is False
    assert result["schemaRepairAttempted"] is True
    assert result["schemaRepairApplied"] is True
    assert result["schemaRepair"]["errorCount"] == 1
    assert result["schemaRepair"]["firstResponseId"] == "resp_fake_real_demo_provider_1"
    assert result["schemaRepair"]["repairResponseId"] == "resp_fake_real_demo_provider_2"
    assert result["responseId"] == "resp_fake_real_demo_provider_2"
    assert result["dslId"] == "exam-real-demo-provider-repaired"
    assert result["generatedStatus"] == "WAITING_REVIEW"


def test_real_llm_demo_grading_normalization_builds_runner_ready_plan(monkeypatch):
    fake_client = FakeClient(grading_dsl_with_runner_field_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="grading",
            input_payload={
                "examDsl": {
                    "kind": "Exam",
                    "metadata": {"id": "exam-real-demo-provider-test"},
                    "spec": {
                        "totalScore": 100,
                        "questions": [
                            {"id": "q1", "score": 20, "gradingRef": "stdout should include review-safe output"},
                            {"id": "q2", "score": 30, "gradingRef": "notebook should produce expected result"},
                            {"id": "q3", "score": 30, "gradingRef": "json metric should match expected value"},
                            {"id": "q4", "score": 20, "gradingRef": "pytest should pass"},
                        ],
                    },
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    grading = result["dsl"]
    checks = {check["id"]: check for check in grading["spec"]["checks"]}
    assert result["schemaValidated"] is True
    assert result["normalization"]["applied"] is True
    assert "set.spec.checks[0].command" in result["normalization"]["patches"]
    assert "set.spec.checks[0].expected" in result["normalization"]["patches"]
    assert "set.spec.checks[1].cellIndex" in result["normalization"]["patches"]
    assert "set.spec.checks[1].expected" in result["normalization"]["patches"]
    assert "set.spec.checks[2].jsonPath" in result["normalization"]["patches"]
    assert "set.spec.checks[2].expectedValue" in result["normalization"]["patches"]
    assert "set.spec.checks[3].path" in result["normalization"]["patches"]
    assert checks["check_q1"]["command"] == "python main.py"
    assert checks["check_q1"]["expected"] == ["stdout should include review-safe output"]
    assert checks["check_q2"]["cellIndex"] == 0
    assert checks["check_q2"]["expected"] == ["notebook should produce expected result"]
    assert checks["check_q3"]["jsonPath"] == "$.score"
    assert checks["check_q3"]["expectedValue"] == "json metric should match expected value"
    assert checks["check_q4"]["path"] == "tests/test_main.py"

    runner_report = GradingRunner().run(grading, "trace_runner_ready")
    assert runner_report["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert all(check["assessmentPlanAlignedWithCheck"] is True for check in runner_report["checks"])

    precheck = build_real_sandbox_precheck_report(grading, "trace_precheck_ready")
    assert precheck["readiness"]["status"] == "READY_FOR_MANUAL_SANDBOX_REVIEW"
    assert precheck["readiness"]["blockers"] == []
    assert precheck["safety"]["sandboxExecuted"] is False


def test_real_llm_demo_grading_aligns_check_ids_to_exam_grading_refs(monkeypatch):
    fake_client = FakeClient(grading_dsl_with_question_id_check_refs())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="grading",
            input_payload={
                "examDsl": {
                    "kind": "Exam",
                    "metadata": {"id": "exam-real-demo-provider-test"},
                    "spec": {
                        "totalScore": 30,
                        "questions": [
                            {"id": "q1-intro", "score": 10, "gradingRef": "q1"},
                            {"id": "q2-code", "score": 10, "gradingRef": "q2"},
                            {"id": "q3-test", "score": 10, "gradingRef": "q3"},
                        ],
                    },
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    grading = result["dsl"]
    checks = grading["spec"]["checks"]
    plans = grading["spec"]["assessmentPlan"]
    assert result["schemaValidated"] is True
    assert [check["id"] for check in checks] == ["q1", "q2", "q3"]
    assert [plan["checkId"] for plan in plans] == ["q1", "q2", "q3"]
    assert [check["score"] for check in checks] == [10, 10, 10]
    assert "set.spec.checks[0].id.fromExamGradingRef" in result["normalization"]["patches"]
    assert "set.spec.checks[1].id.fromExamGradingRef" in result["normalization"]["patches"]
    assert "set.spec.checks[2].id.fromExamGradingRef" in result["normalization"]["patches"]
    assert "set.spec.assessmentPlan.alignedWithChecks" in result["normalization"]["patches"]


def test_real_llm_demo_grading_expands_single_check_to_cover_exam_refs(monkeypatch):
    fake_client = FakeClient(grading_dsl_with_single_generic_check())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="grading",
            input_payload={
                "examDsl": {
                    "kind": "Exam",
                    "metadata": {"id": "exam-real-demo-provider-test"},
                    "spec": {
                        "totalScore": 100,
                        "questions": [
                            {"id": "q1", "score": 30, "gradingRef": "step-1", "answer": "python --version"},
                            {"id": "q2", "score": 40, "gradingRef": "step-2-3", "answer": "def calculate_sum(numbers): ..."},
                            {"id": "q3", "score": 30, "gradingRef": "step-4", "answer": "python demo.py"},
                        ],
                    },
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    grading = result["dsl"]
    checks = grading["spec"]["checks"]
    plans = grading["spec"]["assessmentPlan"]
    assert result["schemaValidated"] is True
    assert [check["id"] for check in checks] == ["step-1", "step-2-3", "step-4"]
    assert [check["score"] for check in checks] == [30, 40, 30]
    assert sum(check["score"] for check in checks) == grading["spec"]["totalScore"]
    assert checks[0]["expected"] == ["python --version"]
    assert [plan["checkId"] for plan in plans] == ["step-1", "step-2-3", "step-4"]
    assert "set.spec.checks.fromExamGradingRefs" in result["normalization"]["patches"]
    assert "set.spec.assessmentPlan.alignedWithChecks" in result["normalization"]["patches"]


def test_real_llm_demo_grading_normalizes_required_limits_type_drift(monkeypatch):
    fake_client = FakeClient(grading_dsl_with_required_limits_type_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="grading",
            input_payload={"examDsl": valid_exam_dsl()},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    limits = result["dsl"]["spec"]["assessmentPlan"][0]["executionPlan"]["requiredLimits"]
    assert limits["cpu"] == "required"
    assert limits["memory"] == "required"
    assert limits["timeout"] == "30s"
    assert result["schemaValidated"] is True
    assert "set.spec.assessmentPlan[0].executionPlan.requiredLimits.cpu" in result["normalization"]["patches"]
    assert "set.spec.assessmentPlan[0].executionPlan.requiredLimits.memory" in result["normalization"]["patches"]
    assert "set.spec.assessmentPlan[0].executionPlan.requiredLimits.timeout" in result["normalization"]["patches"]


def test_real_llm_demo_grading_promotes_spec_aliases(monkeypatch):
    fake_client = FakeClient(grading_dsl_with_spec_aliases())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="grading",
            input_payload={
                "examDsl": {
                    "kind": "Exam",
                    "metadata": {"id": "exam-alias-demo"},
                    "spec": {
                        "totalScore": 100,
                        "questions": [
                            {"id": "q1", "score": 60, "gradingRef": "review boundary"},
                            {"id": "q2", "score": 40, "gradingRef": "import boundary"},
                        ],
                    },
                }
            },
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    grading = result["dsl"]
    checks = grading["spec"]["checks"]
    patches = result["normalization"]["patches"]
    assert result["schemaValidated"] is True
    assert grading["metadata"]["sourceExamId"] == "exam-alias-demo"
    assert grading["spec"]["totalScore"] == 100
    assert grading["spec"]["timeoutSeconds"] == 45
    assert [check["type"] for check in checks] == ["stdout_contains", "log_keyword"]
    assert [check["score"] for check in checks] == [60, 40]
    assert checks[0]["expected"] == ["review boundary"]
    assert checks[1]["expected"] == ["import boundary"]
    assert "set.metadata.sourceExamId.from.examId" in patches
    assert "set.spec.checks.from.gradingRules" in patches
    assert "set.spec.assessmentPlan" in patches


def test_real_llm_demo_grading_normalizes_check_type_alias_drift(monkeypatch):
    fake_client = FakeClient(grading_dsl_with_check_type_alias_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="grading",
            input_payload={"examDsl": valid_exam_dsl()},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    checks = result["dsl"]["spec"]["checks"]
    plans = result["dsl"]["spec"]["assessmentPlan"]
    assert result["schemaValidated"] is True
    assert [check["type"] for check in checks] == [
        "stdout_contains",
        "pytest",
        "notebook_cell",
        "json_field",
        "log_keyword",
    ]
    assert [plan["type"] for plan in plans] == [check["type"] for check in checks]
    assert [plan["runner"] for plan in plans] == [
        "StdoutContainsGrader",
        "PytestGrader",
        "NotebookGrader",
        "JsonFieldGrader",
        "LogKeywordGrader",
    ]
    assert "set.spec.checks[0].type" in result["normalization"]["patches"]
    assert "set.spec.checks[1].type" in result["normalization"]["patches"]
    assert "set.spec.checks[2].type" in result["normalization"]["patches"]
    assert "set.spec.checks[3].type" in result["normalization"]["patches"]
    assert "set.spec.checks[4].type" in result["normalization"]["patches"]

    runner_report = GradingRunner().run(result["dsl"], "trace_alias_ready")
    assert runner_report["assessmentPlanSummary"]["alignedWithChecks"] is True


def test_real_llm_demo_grading_normalizes_expected_token_type_drift(monkeypatch):
    fake_client = FakeClient(grading_dsl_with_expected_token_type_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="grading",
            input_payload={"examDsl": valid_exam_dsl()},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    check = result["dsl"]["spec"]["checks"][0]
    assert result["schemaValidated"] is True
    assert check["expected"] == ["WAITING_REVIEW", "42", "A；B"]
    assert "set.spec.checks[0].expected" in result["normalization"]["patches"]


def test_real_llm_demo_ppt_normalizes_slide_shape_drift(monkeypatch):
    fake_client = FakeClient(ppt_dsl_with_slide_shape_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="ppt",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"title": "真实 LLM Demo 实验"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    ppt = result["dsl"]
    slides = ppt["spec"]["slides"]
    assert result["schemaValidated"] is True
    assert ppt["metadata"]["id"] == "ppt-real-demo-provider-test"
    assert ppt["metadata"]["audience"] == "平台开发者"
    assert ppt["metadata"]["durationMinutes"] == 45
    assert ppt["spec"]["theme"] == {"style": "clean", "language": "zh-CN"}
    assert slides[0]["id"] == "1"
    assert slides[0]["type"] == "title"
    assert slides[0]["title"] == "演示封面"
    assert slides[0]["subtitle"] == "真实 LLM；DSL 审核"
    assert slides[0]["bullets"] == ["统一进入 WAITING_REVIEW"]
    assert slides[1]["type"] == "summary"
    assert slides[1]["id"] == "slide_2"
    assert slides[1]["bullets"] == ["不自动发布", "人工审核后再进入平台实体"]
    assert "set.metadata.id" in result["normalization"]["patches"]
    assert "set.metadata.durationMinutes" in result["normalization"]["patches"]
    assert "set.spec.theme.style" in result["normalization"]["patches"]
    assert "set.spec.slides[0].type" in result["normalization"]["patches"]
    assert "set.spec.slides[0].bullets" in result["normalization"]["patches"]
    assert "set.spec.slides[1].bullets" in result["normalization"]["patches"]


def test_real_llm_demo_ppt_preserves_notes_and_duration_as_review_bullets(monkeypatch):
    fake_client = FakeClient(ppt_dsl_with_slide_notes_and_duration_drift())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="ppt",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"title": "真实 LLM Demo 实验"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    slides = result["dsl"]["spec"]["slides"]
    assert result["schemaValidated"] is True
    assert slides[0]["id"] == "cover"
    assert slides[0]["type"] == "title"
    assert slides[0]["bullets"] == ["讲稿提示：强调课程目标和人工审核边界。", "建议时长：90"]
    assert "speakerNotes" not in slides[0]
    assert "durationSeconds" not in slides[0]
    assert slides[1]["type"] == "summary"
    assert slides[1]["bullets"] == [
        "复盘 DSL 生成",
        "保持 WAITING_REVIEW",
        "讲稿提示：提醒审核 PPTX Artifact；不要自动发布",
        "建议时长：120",
    ]
    assert "notes" not in slides[1]
    assert "duration" not in slides[1]
    assert "set.spec.slides[0].type" in result["normalization"]["patches"]
    assert "set.spec.slides[0].bullets" in result["normalization"]["patches"]
    assert "set.spec.slides[1].type" in result["normalization"]["patches"]
    assert "set.spec.slides[1].bullets" in result["normalization"]["patches"]
    assert "remove.$.spec.slides[0].speakerNotes" in result["normalization"]["patches"]
    assert "remove.$.spec.slides[1].notes" in result["normalization"]["patches"]


def test_real_llm_demo_ppt_promotes_spec_aliases(monkeypatch):
    fake_client = FakeClient(ppt_dsl_with_spec_aliases())

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    result = run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind="ppt",
            input_payload={"labDsl": {"kind": "Lab", "metadata": {"title": "字段别名实验"}}},
            model="test-model",
            explicit_real_call_opt_in=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=lambda **_: fake_client,
    )

    ppt = result["dsl"]
    slides = ppt["spec"]["slides"]
    patches = result["normalization"]["patches"]
    assert result["schemaValidated"] is True
    assert ppt["metadata"]["audience"] == "教师"
    assert ppt["metadata"]["durationMinutes"] == 25
    assert ppt["spec"]["theme"] == {"style": "clean", "language": "zh-CN"}
    assert [slide["type"] for slide in slides] == ["title", "summary"]
    assert slides[1]["bullets"] == ["保持人工审核"]
    assert "set.metadata.audience.from.targetAudience" in patches
    assert "set.spec.theme.from.style" in patches
    assert "set.spec.slides.from.pages" in patches


def test_real_llm_demo_dsl_generation_requires_confirmations(monkeypatch):
    request = RealLlmDemoDslRequest(
        kind="exam",
        input_payload={"source": "demo"},
        model="test-model",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=False,
        confirm_no_auto_publish=True,
    )

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")

    try:
        run_real_llm_demo_dsl_generation(request, root=ROOT, client_factory=lambda **_: FakeClient(valid_exam_dsl()))
    except ProviderError as exc:
        context = build_real_llm_demo_dsl_error_context(exc, request=request, root=ROOT)
        assert exc.code == "REAL_LLM_DEMO_DSL_CONFIRMATION_REQUIRED"
        assert exc.errors == [{"field": "confirm_waiting_review", "reason": "required"}]
        assert context["requestSent"] is False
        assert context["realLlmCalled"] is False
        assert context["secretValueReturned"] is False
        assert context["inputPayloadKeys"] == ["source"]
    else:
        raise AssertionError("expected ProviderError")
