"""Local mock environment model for Phase 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .ai_task import utc_now


class EnvironmentType(StrEnum):
    VM = "vm"
    NOTEBOOK = "notebook"


class EnvironmentStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    RESETTING = "RESETTING"


ALLOWED_ENV_TRANSITIONS: dict[EnvironmentStatus, set[EnvironmentStatus]] = {
    EnvironmentStatus.CREATED: {EnvironmentStatus.RUNNING, EnvironmentStatus.STOPPED},
    EnvironmentStatus.RUNNING: {EnvironmentStatus.STOPPED, EnvironmentStatus.RESETTING},
    EnvironmentStatus.STOPPED: {EnvironmentStatus.RUNNING, EnvironmentStatus.RESETTING},
    EnvironmentStatus.RESETTING: {EnvironmentStatus.STOPPED},
}


@dataclass
class EnvironmentInstance:
    envType: EnvironmentType
    title: str
    image: str
    id: str = field(default_factory=lambda: f"env_{uuid4().hex[:12]}")
    status: EnvironmentStatus = EnvironmentStatus.CREATED
    provider: str = "mock"
    resources: dict[str, Any] = field(default_factory=lambda: {"cpu": 2, "memoryGb": 4})
    createdAt: str = field(default_factory=utc_now)
    updatedAt: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["envType"] = self.envType.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnvironmentInstance":
        payload = dict(data)
        payload["envType"] = EnvironmentType(payload["envType"])
        payload["status"] = EnvironmentStatus(payload["status"])
        return cls(**payload)

    def transition_to(self, next_status: EnvironmentStatus) -> None:
        if next_status not in ALLOWED_ENV_TRANSITIONS[self.status]:
            raise ValueError(
                f"Illegal environment status transition: {self.status.value} -> {next_status.value}"
            )
        self.status = next_status
        self.updatedAt = utc_now()
