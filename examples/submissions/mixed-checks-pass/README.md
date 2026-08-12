# mixed-checks-pass

This submission is a local 100/100 smoke sample for:

```powershell
python lab_cli.py grade stable-v1 --grading templates/grading/examples/mixed-checks.yaml --submission examples/submissions/mixed-checks-pass --output examples/output/grading-stable-v1-docker-full-pass-evidence.json --submission-id docker_full_pass_submission_001 --candidate-id candidate_docker_full_pass --reviewer teacher_1 --image ai-grading-python:0.1 --review-detail-output examples/output/grading-stable-v1-docker-full-pass-review-detail.json --result-preview-output examples/output/grading-stable-v1-docker-full-pass-result-preview.json --fail-on-controlled-unavailable
```

## Inputs

- `result.csv`: satisfies `file_exists`.
- `main.py`: prints `accuracy=0.90` for `stdout_contains`.
- `tests/test_main.py`: pytest check for `accuracy()`.
- `notebooks/analysis.ipynb`: static notebook JSON with cell index `3` containing `accuracy`.
- `metrics.json`: contains `{"accuracy": 0.9}`.
- `logs/train.log`: contains `training complete`.

## Output

The command should produce `GRADING_EVIDENCE_AUTO_REPORT` with `earnedScore=100`, `totalScore=100`, controlled Docker evidence included, and a local `GradingRecord` waiting for human review.

## Limits

This is a local demo fixture. It does not call a real LLM, write production databases, call a real platform backend, or publish content.
