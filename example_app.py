"""Example multi-endpoint Calculator app demonstrating Jarvis SDK usage."""

import jarvis
from pydantic import BaseModel


class AddInput(BaseModel):
    """Input model for the add endpoint."""
    a: float
    b: float


class AddOutput(BaseModel):
    """Output model for the add endpoint."""
    result: float


class SubtractInput(BaseModel):
    """Input model for the subtract endpoint."""
    a: float
    b: float


class SubtractOutput(BaseModel):
    """Output model for the subtract endpoint."""
    result: float


@jarvis.app()
class Calculator:
    """A simple calculator with add and subtract operations.

    This demonstrates:
    - Multiple endpoints in a single app class
    - Shared state via setup() method
    - Pydantic models for input/output validation
    """

    def setup(self):
        """Initialize shared state. Called once on app startup."""
        self.operation_count = 0

    @jarvis.endpoint()
    def add(self, input: AddInput) -> AddOutput:
        """Add two numbers together."""
        self.operation_count += 1
        return AddOutput(result=input.a + input.b)

    @jarvis.endpoint()
    def subtract(self, input: SubtractInput) -> SubtractOutput:
        """Subtract b from a."""
        self.operation_count += 1
        return SubtractOutput(result=input.a - input.b)
