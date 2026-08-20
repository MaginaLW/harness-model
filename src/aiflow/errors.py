"""Stable domain errors for AI Flow."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar


class AiflowError(Exception):
    """Base error with separate human and machine representations."""

    default_code: ClassVar[str] = "AIFLOW_ERROR"

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or self.default_code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        """Return a stable representation suitable for CLI JSON output."""
        return {"code": self.code, "message": self.message, "details": self.details}


class ContractError(AiflowError):
    """A machine contract is missing, unsupported, or invalid."""

    default_code = "CONTRACT_ERROR"


class StorageError(AiflowError):
    """Task storage could not be accessed safely or atomically."""

    default_code = "STORAGE_ERROR"


class StateTransitionError(AiflowError):
    """A requested task state transition is not valid."""

    default_code = "STATE_TRANSITION_ERROR"


class PolicyError(AiflowError):
    """Policy loading or evaluation failed."""

    default_code = "POLICY_ERROR"


class VerificationError(AiflowError):
    """Verification could not produce a valid result."""

    default_code = "VERIFICATION_ERROR"


class GateError(AiflowError):
    """A required task gate is not satisfied."""

    default_code = "GATE_ERROR"
