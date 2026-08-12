from cli.environment import EnvironmentInstance, EnvironmentStatus, EnvironmentType


def test_environment_created_defaults_to_mock_created():
    environment = EnvironmentInstance(envType=EnvironmentType.VM, title="Ubuntu VM", image="ubuntu-22.04")

    assert environment.status == EnvironmentStatus.CREATED
    assert environment.provider == "mock"


def test_environment_can_start_stop_and_reset():
    environment = EnvironmentInstance(envType=EnvironmentType.NOTEBOOK, title="Notebook", image="jupyter/base")

    environment.transition_to(EnvironmentStatus.RUNNING)
    environment.transition_to(EnvironmentStatus.STOPPED)
    environment.transition_to(EnvironmentStatus.RESETTING)
    environment.transition_to(EnvironmentStatus.STOPPED)

    assert environment.status == EnvironmentStatus.STOPPED


def test_environment_illegal_transition_is_rejected():
    environment = EnvironmentInstance(envType=EnvironmentType.VM, title="Ubuntu VM", image="ubuntu-22.04")

    try:
        environment.transition_to(EnvironmentStatus.RESETTING)
    except ValueError as exc:
        assert "CREATED -> RESETTING" in str(exc)
    else:
        raise AssertionError("expected illegal transition to fail")
