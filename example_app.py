"""Example endpoint for testing startup time."""

import jarvis
from pydantic import BaseModel


class Input(BaseModel):
    name: str


class Output(BaseModel):
    message: str


@jarvis.endpoint()
class Greeter:
    def setup(self):
        self.prefix = "Hello"

    def run(self, input: Input) -> Output:
        return Output(message=f"{self.prefix}, {input.name}!")
