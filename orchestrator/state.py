import time
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class ReliabilityMetrics(BaseModel):
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    end_to_end_latency: float = 0.0
    retry_count: int = 0
    rollback_frequency: int = 0
    tasks_total: int = 0
    tasks_completed: int = 0

    @property
    def success_rate(self) -> float:
        if self.tasks_total == 0:
            return 0.0
        return round((self.tasks_completed / self.tasks_total) * 100, 2)


class WorkflowState(BaseModel):
    raw_input: str
    normalized_spec: Any = None
    task_graph: List[Dict] = Field(default_factory=list)
    impact_analysis: Dict = Field(default_factory=dict)
    code_artifacts: Dict[str, str] = Field(default_factory=dict)
    test_metrics: Dict = Field(default_factory=dict)

    # --- Enterprise Orchestration Enhancements ---
    decision_lineage: List[str] = Field(default_factory=list)
    execution_logs: List[str] = Field(default_factory=list)

    # FIX: Use lambda to provide a callable factory for the dictionary
    policy_guardrails: Dict[str, bool] = Field(default_factory=lambda: {
        "security_scan_passed": False,
        "compliance_approved": False,
        "governance_bypassed": False
    })

    metrics: ReliabilityMetrics = Field(default_factory=ReliabilityMetrics)

    # Add inside WorkflowState class:
    risks_and_tradeoffs: List[str] = Field(default_factory=list)
    safety_guardrails_applied: List[str] = Field(default_factory=list)
    final_engineering_summary: str = ""

    def log_decision(self, agent: str, decision: str):
        """Records stateful context lineage across non-linear stages."""
        entry = f"[{agent}] {decision}"
        self.decision_lineage.append(entry)
        self.execution_logs.append(entry)