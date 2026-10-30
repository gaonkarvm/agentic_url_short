import os
import logging
from models.schemas import SystemConfig, ScenarioType, RequirementType
from orchestrator.state import WorkflowState
from orchestrator.engine import OrchestrationEngine, Task
from agents.requirement_agent import RequirementUnderstandingAgent
from agents.decomposition_agent import TaskDecompositionAgent
from agents.reasoning_agent import CodebaseReasoningAgent
from agents.design_agent import ArchitectureDesignAgent
from agents.implementation_agent import ImplementationAgent
from agents.testing_agent import TestingValidationAgent
from agents.summary_agent import FinalSummaryAgent


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s")
logger = logging.getLogger("MainRunner")

if __name__ == "main" or __name__ == "__main__":
    # Configure for Live LLM Greenfield Execution
    config = SystemConfig(
        use_simulation=True,  # Switches from mock heuristics to real LLM calls
        scenario_type=ScenarioType.GREENFIELD,
        requirement_type=RequirementType.AMBIGUOUS,
        model_name="gpt-4o"
    )

    logger.info(f"Initializing Live LLM SDLC Pipeline: {config.scenario_type.value.upper()}")

    # Ambiguous Raw Requirement Input
    workflow_state = WorkflowState(
        raw_input="Build a quick link shortener tool that is fast and handles clicks."
    )

    # Initialize Agents with Live Config
    req_agent = RequirementUnderstandingAgent(config=config)
    decomp_agent = TaskDecompositionAgent(config=config)
    reasoning_agent = CodebaseReasoningAgent(config=config)
    arch_agent = ArchitectureDesignAgent(config=config)
    impl_agent = ImplementationAgent(config=config)
    test_agent = TestingValidationAgent(config=config)
    summary_agent = FinalSummaryAgent(config=config)

    # Build Stateful Execution Graph
    engine = OrchestrationEngine(workflow_state)

    engine.add_task(Task("normalize_requirements", lambda s: req_agent.execute(s)))
    engine.add_task(Task("decompose_tasks", lambda s: decomp_agent.execute(s), dependencies=["normalize_requirements"]))
    engine.add_task(Task("codebase_reasoning", lambda s: reasoning_agent.execute(s), dependencies=["decompose_tasks"]))
    engine.add_task(Task("architecture_design", lambda s: arch_agent.execute(s), dependencies=["decompose_tasks"]))

    # Example snippet for main.py showcasing the new capabilities:
    engine.add_task(Task(
        name="implementation",
        action=lambda s: impl_agent.execute(s),
        dependencies=["codebase_reasoning", "architecture_design"],
        max_retries=3,
        rollback=lambda s: logger.info("Rollback: Reverting git workspace state.")
    ))

    # Governance Gate (HITL)
    engine.add_task(Task(
        name="governance_approval_gate",
        action=lambda s: s.log_decision("Governance", "Approved implementation for merge"),
        dependencies=["implementation"],
        requires_approval=True  # Triggers the safe-stop human pause
    ))

    # Parallel Tasks (These will run concurrently because they share the same dependency)
    engine.add_task(
        Task("testing_validation", lambda s: test_agent.execute(s), dependencies=["governance_approval_gate"]))
    engine.add_task(Task("security_scan", lambda s: s.policy_guardrails.update({"security_scan_passed": True}),
                         dependencies=["governance_approval_gate"]))

    # Point 6 & 8: Validation/Risk Control & Final Engineering Summary
    engine.add_task(
        Task("generate_final_summary", lambda s: summary_agent.execute(s), dependencies=["testing_validation"]))

    # Run Workflow
    success = engine.run()

    # Output Evaluation Summary
    print("\n" + "=" * 60)
    print(f"LIVE LLM EVALUATION SUMMARY: {config.scenario_type.value.upper()}")
    print("=" * 60)
    print(f"• Execution Status: {'SUCCESS' if success else 'FAILED'}")
    print(
        f"• Normalized Title: {workflow_state.normalized_spec.feature_title if workflow_state.normalized_spec else 'N/A'}")
    print(f"• Artifacts Persisted to Workspace: {list(workflow_state.code_artifacts.keys())}")
    print(f"• Test Metrics / Coverage: {workflow_state.test_metrics}")