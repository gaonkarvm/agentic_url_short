import logging
import os
import textwrap
from models.schemas import SystemConfig,RequirementType
from orchestrator.state import WorkflowState

logger = logging.getLogger("FinalSummaryAgent")

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False


class FinalSummaryAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        if not self.config.use_simulation and HAS_LANGCHAIN:
            self.llm = ChatOpenAI(model=config.model_name, temperature=0.1)

    def execute(self, state: WorkflowState) -> None:
        workspace_dir = "./workspace"
        os.makedirs(workspace_dir, exist_ok=True)

        if self.config.use_simulation:
            if self.config.requirement_type == RequirementType.WELL_DEFINED:
                logger.info("[Agent: Final Summary] Generating Final Engineering Summary (SIMULATION)...")

                # Populating structured lists for risk and guardrail tracking
                state.risks_and_tradeoffs = [
                    "Scalability Risks: Redis caching performance is contingent on capacity; a single point of failure could cause downtime.",
                    "Data Consistency: Trade-off between performance and real-time consistency for click analytics counters.",
                    "Security Concerns: Potential exploitation for malicious redirection (phishing); requires robust validation.",
                    "Custom Alias Conflicts: Requires strict uniqueness validation to prevent overwriting existing entries."
                ]
                state.safety_guardrails_applied = [
                    "Unit Testing: Comprehensive test suite in test_main.py covering edge cases and reliability.",
                    "Code Reviews: Regular reviews maintained code quality and best practices adherence.",
                    "Monitoring and Logging: Mechanisms to track system performance and detect anomalies in real-time."
                ]

                state.final_engineering_summary = textwrap.dedent(f'''\
                                # Final Engineering Summary
    
                                ## 1. Plan/Rationale
    
                                The objective was to design and implement a production-grade URL shortener service. The service was required to include core functionalities such as URL redirection APIs, support for custom aliases, click analytics counters, and Redis caching for performance optimization. The rationale behind this project was to create a scalable and efficient service that could handle high traffic and provide real-time analytics, which are essential for modern web applications.
    
                                ## 2. Artifacts Generated
    
                                During the development process, the following artifacts were generated:
    
                                - **architecture.md**: This document outlines the system architecture, detailing the components, their interactions, and the overall design philosophy. It serves as a blueprint for understanding the system's structure and behavior.
    
                                - **main.py**: The primary codebase for the URL shortener service. It includes the implementation of the core functionalities such as URL shortening, redirection, custom alias handling, and integration with Redis for caching.
    
                                - **test_main.py**: A suite of unit tests designed to validate the functionality of the main application. This ensures that the core features work as expected and helps in identifying any regressions during future updates.
    
                                ## 3. Risks/Trade-offs/Failure Scenarios
    
                                - **Scalability Risks**: While Redis caching is implemented to enhance performance, the system's scalability is contingent on the Redis instance's capacity. A single point of failure in Redis could lead to service downtime.
    
                                - **Data Consistency**: There is a trade-off between performance and consistency, especially with click analytics. Real-time analytics may not always reflect the most current data due to eventual consistency in distributed systems.
    
                                - **Security Concerns**: URL shorteners can be exploited for malicious purposes, such as phishing. Implementing robust security measures, such as URL validation and monitoring, is crucial to mitigate these risks.
    
                                - **Custom Alias Conflicts**: Handling conflicts with custom aliases requires careful management to ensure unique mappings and avoid overwriting existing entries.
    
                                ## 4. Validation & Safety Guardrails
    
                                - **Unit Testing**: Comprehensive unit tests in `test_main.py` ensure that each component functions correctly. These tests cover edge cases and typical usage scenarios to validate the system's reliability.
    
                                - **Code Reviews**: Regular code reviews were conducted to maintain code quality and adherence to best practices, ensuring that potential issues are identified and resolved early in the development process.
    
                                - **Monitoring and Logging**: Implementing monitoring and logging mechanisms to track system performance and detect anomalies in real-time, providing a safety net for quick response to potential failures.
    
                                ## 5. Assumptions & Limitations
    
                                - **Assumptions**: It is assumed that the Redis instance will be adequately provisioned to handle the expected load and that network latency will not significantly impact performance.
    
                                - **Limitations**: The current implementation does not include advanced features such as user authentication, which could be necessary for managing user-specific data and permissions. Additionally, the system's ability to handle extremely high traffic loads has not been fully tested, and further optimization may be required for such scenarios.
    
                                In conclusion, the URL shortener service has been developed with a focus on core functionality and performance optimization. While there are inherent risks and limitations, the system is designed to be robust and scalable, with mechanisms in place to ensure reliability and security. Future iterations can build upon this foundation to enhance features and address any identified limitations.
                            ''')
            else:
                logger.info("[Agent: Final Summary] Generating Final Engineering Summary (SIMULATION - Ambiguous)...")
                state.risks_and_tradeoffs = [
                    "Scalability: As the number of users and shortened links grows, the system may face challenges maintaining performance.",
                    "Data Integrity: Ensuring accurate storage and retrieval of links under heavy concurrent load.",
                    "Speed vs. Security: Trade-offs between rapid url shortening and advanced security screening."
                ]
                state.safety_guardrails_applied = [
                    "Unit Testing: Comprehensive test suite in test_main.py covering SQLite session isolation.",
                    "Code Reviews: Maintained code quality for ambiguous input assumptions.",
                    "Monitoring: Basic error handling and logging established."
                ]
                state.final_engineering_summary = textwrap.dedent('''\
                        # Final Engineering Summary

                        ## 1. Plan/Rationale
                        The objective of this project was to develop a quick link shortener tool that is both efficient and capable of handling a high volume of clicks from an ambiguous initial prompt. Baseline assumptions were established to handle click redirection and analytics counters.

                        ## 2. Artifacts Generated
                        - **architecture.md**: System architecture blueprint.
                        - **main.py**: FastAPI implementation with SQLAlchemy and SQLite persistence.
                        - **test_main.py**: Pytest suite validating end-to-end shortening, redirection, and analytics.

                        ## 3. Risks/Trade-offs/Failure Scenarios
                        - **Scalability**: Potential performance bottlenecks under high traffic loads.
                        - **Database Availability**: Single point of failure if the SQLite/SQLAlchemy backend goes offline.

                        ## 4. Validation & Safety Guardrails
                        - **Unit Testing**: Verified status codes, error paths (404 Not Found), and click increments.
                        - **Governance Gate**: Human oversight checkpoint successfully authorized the progression despite initial specification ambiguities.

                        ## 5. Assumptions & Limitations
                        - **Assumptions**: Stable network environment; standard URL shortener behavior expected by users.
                        - **Limitations**: Basic persistence layer configured via SQLite for initial rapid prototyping.
                    ''')

        else:
            logger.info(f"[Agent: Final Summary] Generating with LIVE LLM ({self.config.model_name})...")
            prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are a Principal Software Engineer. Generate a comprehensive 'Final Engineering Summary' in Markdown. "
                 "It MUST include: 1. Plan/Rationale, 2. Artifacts Generated, 3. Risks/Trade-offs/Failure Scenarios, "
                 "4. Validation & Safety Guardrails, and 5. Assumptions & Limitations. Base this entirely on the provided execution state."),
                ("human",
                 "Execution State Overview:\nObjective: {objective}\nArtifacts: {artifacts}\nMetrics: {metrics}")
            ])
            chain = prompt | self.llm
            response = chain.invoke({
                "objective": state.raw_input,
                "artifacts": list(state.code_artifacts.keys()),
                "metrics": state.metrics.model_dump_json()
            })
            state.final_engineering_summary = response.content

            print("\n" + "─" * 50)
            print("🤖 [LLM Response] Final Engineering Summary:")
            print(state.final_engineering_summary)
            print("─" * 50 + "\n")

        # Persist the summary
        file_path = os.path.join(workspace_dir, "engineering_summary.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(state.final_engineering_summary)

        logger.info(f"Persisted artifact to disk: {file_path}")
        state.execution_logs.append("Final engineering summary and risk assessment generated.")