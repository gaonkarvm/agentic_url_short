import logging
import os
from models.schemas import SystemConfig
from orchestrator.state import WorkflowState

logger = logging.getLogger("ArchitectureDesignAgent")

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

class ArchitectureDesignAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        if not self.config.use_simulation and HAS_LANGCHAIN:
            self.llm = ChatOpenAI(model=config.model_name, temperature=0.2)

    def execute(self, state: WorkflowState) -> None:
        workspace_dir = "./workspace"
        os.makedirs(workspace_dir, exist_ok=True)

        if self.config.use_simulation:
            logger.info("[Agent: Architecture Design] Running in SIMULATION mode...")
            doc_content = (
                "# URL Shortener Service Architecture\n\n"
                "## Overview\n\n"
                "The URL Shortener Service is designed to provide efficient URL redirection, "
                "custom alias creation, and click analytics while ensuring high performance and scalability. "
                "The service leverages Redis for caching to optimize performance and reduce latency.\n\n"
                "## Architecture Components\n\n"
                "1. **API Gateway**: Handles incoming requests and routes them to the appropriate service.\n"
                "2. **URL Shortener Service**: Core service responsible for URL shortening, redirection, and analytics.\n"
                "3. **Database / Cache (Redis)**: Stores URL mappings, custom aliases, and click analytics counters.\n\n"
                "## API Endpoints\n\n"
                "### 1. Shorten URL\n"
                "- **Endpoint**: `POST /shorten`\n"
                "- **Description**: Shortens a given URL (supports optional custom aliases).\n"
                "- **Request Body**:\n"
                "  ```json\n"
                "  {\n"
                "    \"url\": \"[https://example.com](https://example.com)\",\n"
                "    \"custom_alias\": \"my-custom-slug\"\n"
                "  }\n"
                "  ```\n\n"
                "### 2. Redirect URL\n"
                "- **Endpoint**: `GET /{short_id}`\n"
                "- **Description**: Resolves the short ID, increments the analytics counter, and redirects to the original URL.\n\n"
                "### 3. Get Click Analytics\n"
                "- **Endpoint**: `GET /analytics/{short_id}`\n"
                "- **Description**: Retrieves current click counts for a given short ID.\n\n"
                "## Non-Functional Requirements\n\n"
                "- **Scalability**: Designed to handle high request volumes efficiently using stateless FastAPI workers.\n"
                "- **Low Latency**: Utilizes in-memory Redis lookup to ensure sub-millisecond redirection times.\n"
                "- **Reliability**: Implements TTL expiration policies and robust error handling for missing or duplicate aliases.\n"
            )
            state.code_artifacts["architecture.md"] = doc_content
        else:
            logger.info(f"[Agent: Architecture Design] Running with LIVE LLM ({self.config.model_name})...")
            prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "Design the architecture, data models, and API endpoints for the requested feature. Output clean markdown."),
                ("human", "Specification:\n{spec}")
            ])
            chain = prompt | self.llm
            response = chain.invoke(
                {"spec": state.normalized_spec.model_dump_json() if state.normalized_spec else state.raw_input})
            state.code_artifacts["architecture.md"] = response.content

            # Print LLM Response
            print("\n" + "─" * 50)
            print("🤖 [LLM Response] Architecture Design (Markdown):")
            print(state.code_artifacts["architecture.md"][:600] + "\n[... truncated ...] ")
            print("─" * 50 + "\n")

        file_path = os.path.join(workspace_dir, "architecture.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(state.code_artifacts["architecture.md"])

        state.execution_logs.append("Architecture design completed and persisted.")