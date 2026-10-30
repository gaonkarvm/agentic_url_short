import logging
from typing import List
from pydantic import BaseModel, Field
from models.schemas import SystemConfig,RequirementType
from orchestrator.state import WorkflowState

logger = logging.getLogger("TaskDecompositionAgent")

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

class TaskNode(BaseModel):
    id: str
    name: str
    dependencies: List[str] = Field(default_factory=list)

class TaskDecompositionOutput(BaseModel):
    tasks: List[TaskNode]

class TaskDecompositionAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        if not self.config.use_simulation and HAS_LANGCHAIN:
            self.llm = ChatOpenAI(model=config.model_name, temperature=0.1).with_structured_output(TaskDecompositionOutput)

    def execute(self, state: WorkflowState) -> None:
        if self.config.use_simulation:
            logger.info("[Agent: Requirement Understanding] Running in SIMULATION mode...")
            if self.config.requirement_type == RequirementType.AMBIGUOUS:
                state.task_graph = [
                    {"id": "T1", "name": "Define Metrics for 'Fast' URL Shortening", "dependencies": []},
                    {"id": "T2", "name": "Define 'Handles Clicks' Requirements", "dependencies": []},
                    {"id": "T3", "name": "Establish Performance Benchmarks for Click Handling", "dependencies": []},
                    {"id": "T4", "name": "Design URL Shortening Algorithm", "dependencies": ["T1"]},
                    {"id": "T5", "name": "Implement URL Shortening Functionality", "dependencies": ["T4"]},
                    {"id": "T6", "name": "Design Click Tracking and Redirection System", "dependencies": ["T2"]},
                    {"id": "T7", "name": "Implement Click Tracking and Redirection", "dependencies": ["T6"]},
                    {"id": "T8", "name": "Develop Basic Analytics for Clicks", "dependencies": ["T6"]},
                    {"id": "T9", "name": "Optimize System for High Volume Click Handling",
                     "dependencies": ["T3", "T7"]},
                    {"id": "T10", "name": "Test URL Shortening Speed", "dependencies": ["T5"]},
                    {"id": "T11", "name": "Test Click Handling and Analytics", "dependencies": ["T7", "T8"]},
                    {"id": "T12", "name": "Deploy Quick Link Shortener Tool", "dependencies": ["T10", "T11"]}
                ]
            else:
                state.task_graph = [
                    {"id": "T1", "name": "Define System Architecture", "dependencies": []},
                    {"id": "T2", "name": "Select Technology Stack", "dependencies": ["T1"]},
                    {"id": "T3", "name": "Design Core Redirection API", "dependencies": ["T1"]},
                    {"id": "T4", "name": "Implement Core Redirection API", "dependencies": ["T3", "T2"]},
                    {"id": "T5", "name": "Design Custom Alias Feature", "dependencies": ["T1"]},
                    {"id": "T6", "name": "Implement Custom Alias Feature", "dependencies": ["T5", "T4"]},
                    {"id": "T7", "name": "Design Click Analytics System", "dependencies": ["T1"]},
                    {"id": "T8", "name": "Implement Click Analytics System", "dependencies": ["T7", "T4"]},
                    {"id": "T9", "name": "Integrate Redis Caching", "dependencies": ["T1", "T4"]},
                    {"id": "T10", "name": "Implement Security Measures", "dependencies": ["T1", "T4"]},
                    {"id": "T11", "name": "Conduct Load Testing", "dependencies": ["T4", "T6", "T8", "T9"]},
                    {"id": "T12", "name": "Deploy to Cloud Environment", "dependencies": ["T4", "T6", "T8", "T9", "T10"]},
                    {"id": "T13", "name": "Monitor and Optimize Performance", "dependencies": ["T12", "T11"]}
                ]

            # Print Simulation Output matching LLM style
            print("\n" + "─" * 50)
            print("🤖 [Simulation Response] Task Decomposition DAG:")
            for task in state.task_graph:
                print(f"  • [{task['id']}] {task['name']} (Deps: {task['dependencies']})")
            print("─" * 50 + "\n")
        else:
            logger.info(f"[Agent: Task Decomposition] Running with LIVE LLM ({self.config.model_name})...")
            prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "Break down the normalized specification into an ordered directed acyclic graph (DAG) of technical tasks with explicit dependencies."),
                ("human", "Normalized Specification:\n{spec}")
            ])
            chain = prompt | self.llm
            spec_text = state.normalized_spec.model_dump_json() if state.normalized_spec else state.raw_input
            result: TaskDecompositionOutput = chain.invoke({"spec": spec_text})
            state.task_graph = [t.model_dump() for t in result.tasks]

            # Print LLM Response
            print("\n" + "─" * 50)
            print("🤖 [LLM Response] Task Decomposition DAG:")
            for task in state.task_graph:
                print(f"  • [{task['id']}] {task['name']} (Deps: {task['dependencies']})")
            print("─" * 50 + "\n")

        state.execution_logs.append("Task decomposition graph generated.")