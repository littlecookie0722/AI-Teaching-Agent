"""Read-only runtime configuration summary for real LLM demo calls."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SECRET_ENV = "OPENAI_API_KEY"
MODEL_ENV = "OPENAI_MODEL"
BASE_URL_ENV = "OPENAI_BASE_URL"
MODE = "REAL_LLM_RUNTIME_CONFIG_SUMMARY"
DEFAULT_DEMO_INPUT = "examples/input/demo-source.md"
DEFAULT_DEMO_REVIEWER = "teacher_1"
DEFAULT_DEMO_REPORT = "examples/output/phase2-real-llm-report.json"
DEFAULT_DEMO_OUTPUTS = {
    "lab": "examples/output/real-llm-lab.json",
    "exam": "examples/output/real-llm-exam.json",
    "grading": "examples/output/real-llm-grading.json",
    "ppt": "examples/output/real-llm-ppt.json",
}


def build_real_llm_runtime_config_summary(
    *,
    root: Path = ROOT,
    environ: Mapping[str, str] | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Return a redacted, read-only summary of OpenAI-compatible runtime env."""

    env = environ or os.environ
    api_key_present = _present(env.get(SECRET_ENV))
    model_arg = _clean(model)
    base_url_arg = _clean(base_url)
    model_env_value = _clean(env.get(MODEL_ENV))
    base_url_env_value = _clean(env.get(BASE_URL_ENV))
    model_value = model_arg or model_env_value
    base_url_value = base_url_arg or base_url_env_value
    model_source = "argument" if model_arg else "environment" if model_env_value else None
    base_url_source = "argument" if base_url_arg else "environment" if base_url_env_value else None
    requirements_path = root / "requirements.txt"
    openai_declared = _requirements_declares_openai(requirements_path)
    ready = api_key_present and bool(model_value)
    missing = []
    if not api_key_present:
        missing.append(SECRET_ENV)
    if not model_value:
        missing.append(MODEL_ENV)
    command_readiness = _build_command_readiness(
        api_key_present=api_key_present,
        model_value=model_value,
        base_url_value=base_url_value,
        model_source=model_source,
        base_url_source=base_url_source,
        missing=missing,
    )
    safe_command_templates = _build_safe_command_templates(
        model_value=model_value,
        base_url_value=base_url_value,
    )
    return {
        "component": "RealLlmRuntimeConfigSummary",
        "mode": MODE,
        "providerId": "openai",
        "apiCompatibility": "openai-compatible",
        "env": {
            SECRET_ENV: {
                "present": api_key_present,
                "valueReturned": False,
                "valueLogged": False,
                "source": "environment" if api_key_present else None,
            },
            MODEL_ENV: {
                "present": bool(model_value),
                "value": model_value,
                "source": model_source,
                "envPresent": bool(model_env_value),
                "argumentProvided": bool(model_arg),
            },
            BASE_URL_ENV: {
                "present": bool(base_url_value),
                "value": base_url_value,
                "source": base_url_source,
                "envPresent": bool(base_url_env_value),
                "argumentProvided": bool(base_url_arg),
                "optional": True,
            },
        },
        "requirements": {
            "path": "requirements.txt",
            "exists": requirements_path.exists(),
            "openaiDeclared": openai_declared,
        },
        "readyForRealLlmCommand": ready,
        "missingRequiredEnv": missing,
        "commandReadiness": command_readiness,
        "safeCommandTemplates": safe_command_templates,
        "recommendedCliDefaults": {
            "modelSource": model_source or "--model",
            "baseUrlSource": base_url_source or "--base-url optional",
            "apiKeySource": SECRET_ENV,
        },
        "supportedCommands": [
            "provider real-llm-minimal-poc run",
            "phase2 workflow run --provider-mode real-llm",
            "review real-dsl-revision --provider-mode real-llm",
        ],
        "safety": {
            "readOnly": True,
            "sdkImported": False,
            "clientCreated": False,
            "requestSent": False,
            "realLlmCalled": False,
            "networkAccess": False,
            "secretValueReturned": False,
            "secretValueLogged": False,
            "taskCreated": False,
            "artifactCreated": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }


def _build_command_readiness(
    *,
    api_key_present: bool,
    model_value: str | None,
    base_url_value: str | None,
    model_source: str | None,
    base_url_source: str | None,
    missing: list[str],
) -> dict[str, Any]:
    can_run = api_key_present and bool(model_value)
    if not api_key_present:
        next_action = "set_api_key_env"
    elif not model_value:
        next_action = "provide_model_argument_or_env"
    else:
        next_action = "run_real_llm_workflow_with_explicit_confirmations"

    return {
        "canRunWithCurrentEnvironment": can_run,
        "missingBeforeRun": list(missing),
        "nextAction": next_action,
        "apiKey": {
            "envName": SECRET_ENV,
            "present": api_key_present,
            "valueReturned": False,
            "valueLogged": False,
        },
        "model": {
            "required": True,
            "value": model_value,
            "source": model_source,
            "acceptedSources": ["--model", MODEL_ENV],
        },
        "baseUrl": {
            "required": False,
            "value": base_url_value,
            "source": base_url_source,
            "acceptedSources": ["--base-url", BASE_URL_ENV],
        },
    }


def _build_safe_command_templates(
    *,
    model_value: str | None,
    base_url_value: str | None,
) -> dict[str, Any]:
    model_arg = model_value or "<model-name>"
    base_url_arg = base_url_value or "<openai-compatible-base-url>"
    runtime_args = [
        "python",
        "lab_cli.py",
        "provider",
        "real-llm-runtime-config",
        "--model",
        model_arg,
    ]
    workflow_args = [
        "python",
        "lab_cli.py",
        "phase2",
        "workflow",
        "run",
        "--input",
        DEFAULT_DEMO_INPUT,
        "--reviewer",
        DEFAULT_DEMO_REVIEWER,
        "--output",
        DEFAULT_DEMO_REPORT,
        "--provider-mode",
        "real-llm",
        "--real-llm-lab-output",
        DEFAULT_DEMO_OUTPUTS["lab"],
        "--real-llm-exam-output",
        DEFAULT_DEMO_OUTPUTS["exam"],
        "--real-llm-grading-output",
        DEFAULT_DEMO_OUTPUTS["grading"],
        "--real-llm-ppt-output",
        DEFAULT_DEMO_OUTPUTS["ppt"],
        "--model",
        model_arg,
        "--max-output-tokens",
        "2600",
        "--explicit-real-call-opt-in",
        "--confirm-real-dsl",
        "--confirm-waiting-review",
        "--confirm-no-auto-publish",
    ]
    if base_url_value:
        runtime_args.extend(["--base-url", base_url_arg])
        workflow_args.extend(["--base-url", base_url_arg])

    return {
        "secretEnvPowerShell": '$env:OPENAI_API_KEY="<your-api-key>"',
        "runtimeConfigCheckArgs": runtime_args,
        "workflowRunArgs": workflow_args,
        "placeholders": {
            "apiKey": "<your-api-key>",
            "model": None if model_value else "<model-name>",
            "baseUrl": None if base_url_value else "<openai-compatible-base-url>",
        },
        "defaultOutputs": {
            "report": DEFAULT_DEMO_REPORT,
            **DEFAULT_DEMO_OUTPUTS,
        },
        "notes": [
            "Templates never include an API key value.",
            "The runtime config check is read-only and sends no request.",
            "The workflow command sends a real LLM request only after the operator sets the API key environment variable and keeps explicit confirmations.",
        ],
    }


def _clean(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _present(value: str | None) -> bool:
    return bool(_clean(value))


def _requirements_declares_openai(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(_line_declares_openai(line) for line in content.splitlines())


def _line_declares_openai(line: str) -> bool:
    stripped = line.strip().lower()
    return bool(stripped) and not stripped.startswith("#") and (
        stripped == "openai" or stripped.startswith(("openai=", "openai>", "openai<", "openai~", "openai["))
    )
