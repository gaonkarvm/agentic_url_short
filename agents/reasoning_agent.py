import logging
import os
from typing import List
from pydantic import BaseModel, Field
from models.schemas import SystemConfig, ScenarioType
from orchestrator.state import WorkflowState

logger = logging.getLogger("CodebaseReasoningAgent")

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

class ImpactAnalysisOutput(BaseModel):
    impacted_files: List[str]
    risk_assessment: str
    dependencies_verified: List[str]

class CodebaseReasoningAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        if not self.config.use_simulation and HAS_LANGCHAIN:
            self.llm = ChatOpenAI(model=config.model_name, temperature=0.1).with_structured_output(ImpactAnalysisOutput)

    def execute(self, state: WorkflowState) -> None:
        workspace_dir = "./workspace"
        existing_codebase_context = ""

        if os.path.exists(workspace_dir):
            logger.info(f"[Agent: Codebase Reasoning] Scanning workspace directory '{workspace_dir}' for existing code...")
            for root, dirs, files in os.walk(workspace_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            existing_codebase_context += f"\n--- File: {file} ---\n{f.read()}\n"
                    except Exception as e:
                        logger.warning(f"Could not read file {file_path}: {e}")

        if self.config.scenario_type == ScenarioType.GREENFIELD:
            logger.info("[Agent: Codebase Reasoning] GREENFIELD mode: Initializing new workspace.")
            state.impact_analysis = {"status": "Greenfield repository initialization."}
        elif self.config.scenario_type == ScenarioType.BROWNFIELD:
            logger.info("[Agent: Codebase Reasoning] BROWNFIELD mode active. Analyzing existing code structure.")
            if self.config.use_simulation:
                found_files = [f for f in os.listdir(workspace_dir)] if os.path.exists(workspace_dir) else []
                state.impact_analysis = {
                    "scanned_files": found_files if found_files else ["main.py"],
                    "impacted_files": ["main.py"],
                    "risk_assessment": "Low regression risk; additive schema and endpoint extension.",
                    "dependencies_verified": ["FastAPI", "Redis"]
                }
            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "Perform codebase reasoning and impact analysis for a brownfield scenario. Determine what modules are impacted."),
                    ("human", "Objective: {objective}\n\nExisting Codebase:\n{codebase_context}")
                ])
                chain = prompt | self.llm
                result: ImpactAnalysisOutput = chain.invoke({
                    "objective": state.raw_input,
                    "codebase_context": existing_codebase_context or "No existing code found."
                })
                state.impact_analysis = result.model_dump()
        else:
            state.impact_analysis = {"status": "Test and Documentation audit mode."}

        state.execution_logs.append("Codebase reasoning completed.")