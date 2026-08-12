from cli.ai_task import AiTask, ReviewAction, TaskStatus, create_review_audit_event, create_waiting_review_task
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.workflow import WorkflowStatus, create_workflow_run, create_workflow_step


def test_generated_content_defaults_to_waiting_review():
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )

    assert task.status == TaskStatus.WAITING_REVIEW


def test_waiting_review_can_be_approved_and_completed():
    task = AiTask(taskType="LAB_GENERATION", title="Mock lab", inputType="markdown", inputRef="demo.md")

    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
    task.transition_to(TaskStatus.COMPLETED)

    assert task.status == TaskStatus.COMPLETED
    assert task.reviewer == "teacher_1"
    assert task.reviewedAt is not None


def test_waiting_review_reject_requires_reason():
    task = AiTask(taskType="LAB_GENERATION", title="Mock lab", inputType="markdown", inputRef="demo.md")

    try:
        task.transition_to(TaskStatus.REJECTED, reviewer="teacher_1")
    except ValueError as exc:
        assert "requires a reason" in str(exc)
    else:
        raise AssertionError("expected reject without reason to fail")


def test_illegal_status_transition_is_rejected():
    task = AiTask(taskType="LAB_GENERATION", title="Mock lab", inputType="markdown", inputRef="demo.md")

    try:
        task.transition_to(TaskStatus.COMPLETED)
    except ValueError as exc:
        assert "WAITING_REVIEW -> COMPLETED" in str(exc)
    else:
        raise AssertionError("expected direct completed transition to fail")


def test_review_transition_requires_reviewer():
    task = AiTask(taskType="LAB_GENERATION", title="Mock lab", inputType="markdown", inputRef="demo.md")

    try:
        task.transition_to(TaskStatus.APPROVED)
    except ValueError as exc:
        assert "requires a reviewer" in str(exc)
    else:
        raise AssertionError("expected approve without reviewer to fail")


def test_create_review_audit_event_records_mock_review_boundary():
    task = AiTask(taskType="LAB_GENERATION", title="Mock lab", inputType="markdown", inputRef="demo.md")
    from_status = task.status
    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")

    event = create_review_audit_event(
        task=task,
        action=ReviewAction.APPROVE,
        actor="teacher_1",
        from_status=from_status,
        to_status=task.status,
        trace_id="trace_test",
    )

    assert event.taskId == task.id
    assert event.action == ReviewAction.APPROVE
    assert event.fromStatus == TaskStatus.WAITING_REVIEW
    assert event.toStatus == TaskStatus.APPROVED
    assert event.mode == "MOCK_ONLY"
    assert event.realPublish is False


def test_create_operation_audit_event_records_phase1_safety_flags():
    event = create_operation_audit_event(
        action=OperationAction.MOCK_GRADING_RUN,
        resource_type=OperationResourceType.GRADING_REPORT,
        resource_id="grading_report_demo",
        actor="lab-cli",
        trace_id="trace_test",
        after_state="COMPLETED",
        detail={"sandboxExecuted": False},
    )

    assert event.action == OperationAction.MOCK_GRADING_RUN
    assert event.resourceType == OperationResourceType.GRADING_REPORT
    assert event.mode == "MOCK_ONLY"
    assert event.realLlmCalled is False
    assert event.realCloudResourceChanged is False
    assert event.contestantCodeExecuted is False
    assert event.realPublish is False


def test_create_workflow_run_records_phase1_safety_flags():
    run = create_workflow_run(
        workflow_id="phase1_main_demo",
        input_ref="examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_test",
        report_path="examples/output/demo-report.json",
        steps=[
            create_workflow_step("generate_lab_dsl", 1, {"status": "WAITING_REVIEW"}),
            create_workflow_step("mock_grade_run", 2, {"sandboxExecuted": False}),
        ],
    )

    assert run.workflowId == "phase1_main_demo"
    assert run.status == WorkflowStatus.COMPLETED
    assert run.mode == "MOCK_ONLY"
    assert run.reviewRequired is True
    assert run.publishBlockedUntilApproved is True
    assert run.realLlmCalled is False
    assert run.realCloudResourceChanged is False
    assert run.sandboxExecuted is False
    assert run.contestantCodeExecuted is False
    assert run.realPublish is False
    assert [step.name for step in run.steps] == ["generate_lab_dsl", "mock_grade_run"]
