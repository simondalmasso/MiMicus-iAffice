from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProgressLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed_steps: list[str] = Field(default_factory=list)
    remaining_uncertainty: float = 1.0
    stagnation_count: int = 0
    replan_reasons: list[str] = Field(default_factory=list)

    def advance(self, step: str, uncertainty: float) -> None:
        previous = self.remaining_uncertainty
        self.completed_steps.append(step)
        self.remaining_uncertainty = min(1.0, max(0.0, uncertainty))
        if self.remaining_uncertainty >= previous - 1e-9:
            self.stagnation_count += 1
        else:
            self.stagnation_count = 0
        if self.stagnation_count >= 2:
            self.replan_reasons.append("two no-progress steps")
