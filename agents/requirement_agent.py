import logging
import os
from models.schemas import NormalizedRequirement, SystemConfig, RequirementType
from orchestrator.state import WorkflowState

logger = logging.getLogger("RequirementUnderstandingAgent")

# Explicitly import LangChain dependencies with clear error handling
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    ChatOpenAI = None
    ChatPromptTemplate = None


class RequirementUnderstandingAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        if not self.config.use_simulation:
            if not HAS_LANGCHAIN:
                raise ImportError(
                    "LangChain is required for live LLM execution. Run `pip install langchain-openai langchain-core`.")
            if not os.environ.get("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY environment variable must be set for live LLM execution.")

            # Bind the LLM directly to the Pydantic schema for structured JSON parsing
            self.llm = ChatOpenAI(
                model=config.model_name,
                temperature=config.temperature
            ).with_structured_output(NormalizedRequirement)

    def execute(self, state: WorkflowState) -> None:
        if self.config.use_simulation:
            logger.info("[Agent: Requirement Understanding] Running in SIMULATION mode...")
            if self.config.requirement_type == RequirementType.AMBIGUOUS:
                logger.info("[Agent: Requirement Understanding] Running in SIMULATION mode (Ambiguous)...")
                state.normalized_spec = NormalizedRequirement(
                    feature_title="Quick Link Shortener Tool",
                    objective="To develop a tool that shortens URLs quickly and efficiently handles user clicks on the shortened links.",
                    functional_scope=[
                        "Shorten long URLs into shorter versions.",
                        "Track and handle user clicks on the shortened URLs."
                    ],
                    non_functional_constraints=[
                        "The tool must be fast in processing URL shortening requests.",
                        "The tool should efficiently handle a high volume of clicks without performance degradation."
                    ],
                    ambiguities_detected=[
                        "What specific metrics define 'fast' for URL shortening?",
                        "What does 'handles clicks' entail? Is it just tracking, or does it include redirecting and analytics?",
                        "Are there any specific performance benchmarks or thresholds for handling clicks?"
                    ],
                    assumptions_made=[
                        "The tool should provide basic analytics for the clicks, such as count and timestamp.",
                        "The tool should redirect users to the original URL when a shortened link is clicked."
                    ],
                    confidence_score=0.7,
                    requires_human_clarification=True
                )
                print("\n" + "─" * 50)
                print("🤖 [Simulation Response] Requirement Understanding (Ambiguous):")
                print(state.normalized_spec.model_dump_json(indent=2))
                print("─" * 50 + "\n")
            else:
                state.normalized_spec = NormalizedRequirement(
                    feature_title="URL Shortener Service",
                    objective=(
                        "To develop a production-grade URL shortener service that provides "
                        "efficient URL redirection, custom alias creation, "
                        "click analytics, and optimized performance through caching."
                    ),
                    functional_scope=[
                        "Implement core redirection APIs to handle URL shortening and redirection.",
                        "Support custom alias creation for shortened URLs.",
                        "Track and provide analytics on the number of clicks for each shortened URL.",
                        "Integrate Redis caching to improve performance and reduce latency."
                    ],
                    non_functional_constraints=[
                        "The service must be scalable to handle a large number of requests.",
                        "Ensure high availability and reliability of the service.",
                        "Optimize for low latency in URL redirection.",
                        "Implement security measures to prevent misuse and ensure data integrity."
                    ],
                    ambiguities_detected=[
                        "The requirement does not specify the expected scale or number of requests per second the service should handle.",
                        "Details on the level of analytics (e.g., geographic data, time-based trends) are not provided.",
                        "No information on the security measures or protocols to be implemented is given."
                    ],
                    assumptions_made=[
                        "The service should be able to handle a high volume of requests typical for a production-grade application.",
                        "Basic click analytics such as total click count is required, but not detailed analytics.",
                        "Redis is chosen for caching due to its performance benefits, but other caching mechanisms are not considered."
                    ],
                    confidence_score=0.95,
                    requires_human_clarification=False
                )
                print("\n" + "─" * 50)
                print("🤖 [Simulation Response] Requirement Understanding:")
                print(state.normalized_spec.model_dump_json(indent=2))
                print("─" * 50 + "\n")
        else:
            logger.info(f"[Agent: Requirement Understanding] Running with LIVE LLM ({self.config.model_name})...")
            prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are an expert software engineering lead. Analyze the raw requirement, extract its objective, scope, and non-functional constraints, and identify ambiguities. Calculate a confidence score between 0.0 and 1.0."),
                ("human", "Raw Requirement:\n{raw_text}")
            ])
            logger.info(f" Running with prompt : ({prompt})...")
            chain = prompt | self.llm
            state.normalized_spec = chain.invoke({"raw_text": state.raw_input})

            # Print LLM Response
            print("\n" + "─" * 50)
            print("🤖 [LLM Response] Requirement Understanding:")
            print(state.normalized_spec.model_dump_json(indent=2))
            print("─" * 50 + "\n")

        state.execution_logs.append("Requirement successfully normalized.")