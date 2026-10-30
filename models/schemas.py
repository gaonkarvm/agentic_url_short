from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    ROLLED_BACK = "ROLLED_BACK"

class ScenarioType(Enum):
    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"
    TEST_DOC_IMPROVEMENT = "test_doc_improvement"

class RequirementType(Enum):
    WELL_DEFINED = "well_defined"
    AMBIGUOUS = "ambiguous"

class SystemConfig(BaseModel):
    use_simulation: bool = True
    scenario_type: ScenarioType = ScenarioType.GREENFIELD
    requirement_type: RequirementType = RequirementType.WELL_DEFINED
    model_name: str = "gpt-4o"
    temperature: float = 0.0  # Added temperature field

class NormalizedRequirement(BaseModel):
    feature_title: str
    objective: str
    functional_scope: List[str]
    non_functional_constraints: List[str]
    ambiguities_detected: List[str]
    assumptions_made: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    requires_human_clarification: bool