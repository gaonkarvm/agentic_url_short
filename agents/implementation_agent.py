import logging
import os
import textwrap
from models.schemas import SystemConfig, ScenarioType,RequirementType
from orchestrator.state import WorkflowState

logger = logging.getLogger("ImplementationAgent")

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False


class ImplementationAgent:
    def __init__(self, config: SystemConfig):
        self.config = config
        if not self.config.use_simulation and HAS_LANGCHAIN:
            self.llm = ChatOpenAI(model=config.model_name, temperature=0.2)

    def execute(self, state: WorkflowState) -> None:
        workspace_dir = "./workspace"
        os.makedirs(workspace_dir, exist_ok=True)

        # Read existing codebase context if available (useful for Brownfield LLM prompt)
        existing_code = ""
        workspace_main = os.path.join(workspace_dir, "main.py")
        if os.path.exists(workspace_main):
            try:
                with open(workspace_main, "r", encoding="utf-8") as f:
                    existing_code = f.read()
            except Exception as e:
                logger.warning(f"Could not read existing main.py: {e}")

        if self.config.use_simulation:
            logger.info("[Agent: Implementation] Running in SIMULATION mode...")
            if self.config.scenario_type == ScenarioType.GREENFIELD:
                if self.config.requirement_type == RequirementType.WELL_DEFINED:
                    code_content = textwrap.dedent('''\
                        from fastapi import FastAPI, HTTPException, Depends
                        from pydantic import BaseModel, HttpUrl
                        from typing import Optional
                        from redis import Redis
                        import hashlib
                        import uvicorn
    
                        app = FastAPI()
    
                        # Initialize Redis client
                        redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
                        # Constants
                        BASE_URL = "http://short.ly/"
                        URL_EXPIRATION_SECONDS = 60 * 60 * 24 * 365  # 1 year
    
                        class URLRequest(BaseModel):
                            url: HttpUrl
                            custom_alias: Optional[str] = None
    
                        class URLResponse(BaseModel):
                            short_url: str
    
                        def generate_short_id(url: str) -> str:
                            return hashlib.md5(url.encode()).hexdigest()[:6]
    
                        @app.post("/shorten", response_model=URLResponse)
                        async def shorten_url(request: URLRequest):
                            if request.custom_alias:
                                if redis_client.exists(request.custom_alias):
                                    raise HTTPException(status_code=400, detail="Custom alias already in use.")
                                short_id = request.custom_alias
                            else:
                                short_id = generate_short_id(request.url)
    
                            redis_client.setex(short_id, URL_EXPIRATION_SECONDS, request.url)
                            redis_client.setex(f"clicks:{short_id}", URL_EXPIRATION_SECONDS, 0)
    
                            return URLResponse(short_url=f"{BASE_URL}{short_id}")
    
                        @app.get("/{short_id}")
                        async def redirect_url(short_id: str):
                            original_url = redis_client.get(short_id)
                            if not original_url:
                                raise HTTPException(status_code=404, detail="URL not found.")
    
                            redis_client.incr(f"clicks:{short_id}")
                            return {"url": original_url}
    
                        @app.get("/analytics/{short_id}")
                        async def get_click_analytics(short_id: str):
                            click_count = redis_client.get(f"clicks:{short_id}")
                            if click_count is None:
                                raise HTTPException(status_code=404, detail="Analytics not found.")
                            return {"click_count": int(click_count)}
    
                        if __name__ == "__main__":
                            uvicorn.run(app, host="0.0.0.0", port=8000)
                    ''')
                else:
                    logger.info("[Agent: Implementation] Running in SIMULATION mode (Ambiguous)...")
                    code_content = textwrap.dedent('''\
                            from fastapi import FastAPI, HTTPException, Depends
                            from pydantic import BaseModel, HttpUrl
                            from sqlalchemy import create_engine, Column, String, Integer, DateTime, func
                            from sqlalchemy.ext.declarative import declarative_base
                            from sqlalchemy.orm import sessionmaker, Session
                            import string
                            import random
                            import datetime

                            DATABASE_URL = "sqlite:///./test.db"

                            Base = declarative_base()
                            engine = create_engine(DATABASE_URL)
                            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

                            app = FastAPI(title="Quick Link Shortener Tool")

                            class URL(Base):
                                __tablename__ = "urls"
                                id = Column(Integer, primary_key=True, index=True)
                                original_url = Column(String, nullable=False)
                                short_url = Column(String, unique=True, index=True)
                                clicks = Column(Integer, default=0)
                                created_at = Column(DateTime, default=func.now())

                            Base.metadata.create_all(bind=engine)

                            class URLCreate(BaseModel):
                                original_url: HttpUrl

                            def get_db():
                                db = SessionLocal()
                                try:
                                    yield db
                                finally:
                                    db.close()

                            def generate_short_url():
                                return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

                            @app.post("/shorten", response_model=dict)
                            def create_short_url(url_create: URLCreate, db: Session = Depends(get_db)):
                                short_url = generate_short_url()
                                db_url = URL(original_url=str(url_create.original_url), short_url=short_url)
                                db.add(db_url)
                                db.commit()
                                db.refresh(db_url)
                                return {"short_url": db_url.short_url}

                            @app.get("/{short_url}")
                            def redirect_to_original(short_url: str, db: Session = Depends(get_db)):
                                db_url = db.query(URL).filter(URL.short_url == short_url).first()
                                if db_url is None:
                                    raise HTTPException(status_code=404, detail="Short URL not found")
                                db_url.clicks += 1
                                db.commit()
                                return {"original_url": db_url.original_url}

                            @app.get("/analytics/{short_url}", response_model=dict)
                            def get_url_analytics(short_url: str, db: Session = Depends(get_db)):
                                db_url = db.query(URL).filter(URL.short_url == short_url).first()
                                if db_url is None:
                                    raise HTTPException(status_code=404, detail="Short URL not found")
                                return {
                                    "original_url": db_url.original_url,
                                    "clicks": db_url.clicks,
                                    "created_at": db_url.created_at
                                }
                        ''')

                state.code_artifacts["main.py"] = code_content

            else:
                # BROWNFIELD FULL FILE SIMULATION (Includes original endpoints + new summary endpoint)
                code_content = textwrap.dedent('''\
                    from fastapi import FastAPI, HTTPException, Depends
                    from pydantic import BaseModel, HttpUrl
                    from typing import Optional
                    from redis import Redis
                    import hashlib
                    import uvicorn

                    app = FastAPI()

                    # Initialize Redis client
                    redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)

                    # Constants
                    BASE_URL = "http://short.ly/"
                    URL_EXPIRATION_SECONDS = 60 * 60 * 24 * 365  # 1 year

                    class URLRequest(BaseModel):
                        url: HttpUrl
                        custom_alias: Optional[str] = None

                    class URLResponse(BaseModel):
                        short_url: str

                    def generate_short_id(url: str) -> str:
                        return hashlib.md5(url.encode()).hexdigest()[:6]

                    @app.post("/shorten", response_model=URLResponse)
                    async def shorten_url(request: URLRequest):
                        if request.custom_alias:
                            if redis_client.exists(request.custom_alias):
                                raise HTTPException(status_code=400, detail="Custom alias already in use.")
                            short_id = request.custom_alias
                        else:
                            short_id = generate_short_id(request.url)

                        redis_client.setex(short_id, URL_EXPIRATION_SECONDS, request.url)
                        redis_client.setex(f"clicks:{short_id}", URL_EXPIRATION_SECONDS, 0)

                        return URLResponse(short_url=f"{BASE_URL}{short_id}")

                    @app.get("/{short_id}")
                    async def redirect_url(short_id: str):
                        original_url = redis_client.get(short_id)
                        if not original_url:
                            raise HTTPException(status_code=404, detail="URL not found.")

                        redis_client.incr(f"clicks:{short_id}")
                        return {"url": original_url}

                    @app.get("/analytics/{short_id}")
                    async def get_click_analytics(short_id: str):
                        click_count = redis_client.get(f"clicks:{short_id}")
                        if click_count is None:
                            raise HTTPException(status_code=404, detail="Analytics not found.")
                        return {"click_count": int(click_count)}

                    # BROWNFIELD ENHANCEMENT: Aggregate Analytics Summary Endpoint
                    @app.get("/analytics/summary")
                    async def get_analytics_summary():
                        keys = redis_client.keys("clicks:*")
                        total_links = len(keys)
                        total_clicks = sum(int(redis_client.get(k) or 0) for k in keys)
                        return {"total_short_links": total_links, "aggregate_clicks": total_clicks}

                    if __name__ == "__main__":
                        uvicorn.run(app, host="0.0.0.0", port=8000)
                ''')
            state.code_artifacts["main.py"] = code_content
        else:
            logger.info(f"[Agent: Implementation] Running with LIVE LLM ({self.config.model_name})...")

            if self.config.scenario_type == ScenarioType.BROWNFIELD:
                prompt = ChatPromptTemplate.from_messages([
                    ("system",
                     "You are an expert software engineer performing a Brownfield feature enhancement. "
                     "Modify the existing main.py code to implement the requested feature. "
                     "CRITICAL: You MUST output the ENTIRE updated Python file code inside a markdown code block, incorporating both existing code and the new enhancement. Do not output a patch, diff, or delta."),
                    ("human", "Existing Codebase:\n{existing_code}\n\nEnhancement Request:\n{objective}")
                ])
                chain = prompt | self.llm
                response = chain.invoke({
                    "existing_code": existing_code or "# No existing code found",
                    "objective": state.raw_input
                })
            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("system",
                     "Write clean, production-grade Python FastAPI code for a URL shortener service. Output ONLY valid Python code inside a markdown code block."),
                    ("human", "Specification:\n{spec}\n\nObjective: {objective}")
                ])
                chain = prompt | self.llm
                response = chain.invoke({
                    "spec": state.normalized_spec.model_dump_json() if state.normalized_spec else state.raw_input,
                    "objective": state.raw_input
                })

            code_content = response.content
            if "```python" in code_content:
                code_content = code_content.split("```python")[1].split("```")[0].strip()
            elif "```" in code_content:
                code_content = code_content.split("```")[1].split("```")[0].strip()
            state.code_artifacts["main.py"] = code_content

            # Print LLM Response
            print("\n" + "─" * 50)
            print("🤖 [LLM Response] Generated Full Implementation Code (main.py):")
            print(state.code_artifacts["main.py"])
            print("─" * 50 + "\n")

        for filename, content in state.code_artifacts.items():
            file_path = os.path.join(workspace_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Persisted artifact to disk: {file_path}")

        state.execution_logs.append("Implementation artifacts generated and persisted.")