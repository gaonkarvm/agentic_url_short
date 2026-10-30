import logging
import time
import concurrent.futures
from typing import Callable, List, Dict
from models.schemas import TaskStatus
from orchestrator.state import WorkflowState

logger = logging.getLogger("OrchestrationEngine")


class Task:
    def __init__(self, name: str, action: Callable[[WorkflowState], None],
                 dependencies: List[str] = None, requires_approval: bool = False,
                 max_retries: int = 3, fallback: Callable[[WorkflowState], None] = None,
                 rollback: Callable[[WorkflowState], None] = None):
        self.name = name
        self.action = action
        self.dependencies = dependencies or []
        self.requires_approval = requires_approval
        self.max_retries = max_retries
        self.fallback = fallback
        self.rollback = rollback
        self.status = TaskStatus.PENDING


class OrchestrationEngine:
    def __init__(self, state: WorkflowState):
        self.state = state
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task):
        """Allows dynamic re-planning by adding tasks at runtime."""
        self.tasks[task.name] = task
        self.state.metrics.tasks_total = len(self.tasks)

    def _execute_task_with_retry(self, task: Task) -> bool:
        """Executes a single task with bounded retries, fallbacks, and HITL gates."""
        attempts = 0

        # Human-in-the-Loop Gate
        if task.requires_approval:
            logger.warning(f"[HITL Gate] Task '{task.name}' paused for human review.")
            # Simulate approval (In a real system, this suspends state to a DB waiting for API callback)
            logger.info(f"[Approval Granted] Proceeding with high-impact action: {task.name}")
            self.state.log_decision("Governance Gate", f"Operator approved '{task.name}'")

        while attempts < task.max_retries:
            attempts += 1
            try:
                task.status = TaskStatus.RUNNING
                logger.info(f"Executing: '{task.name}' (Attempt {attempts}/{task.max_retries})")

                # Execute Action
                task.action(self.state)

                task.status = TaskStatus.SUCCESS
                self.state.metrics.tasks_completed += 1
                return True

            except Exception as e:
                logger.error(f"Task '{task.name}' failed on attempt {attempts}: {e}")
                self.state.metrics.retry_count += 1
                if attempts >= task.max_retries:
                    break
                time.sleep(1)  # Bounded backoff

        # Fallback Protocol
        if task.fallback:
            logger.warning(f"Triggering fallback for '{task.name}'...")
            try:
                task.fallback(self.state)
                task.status = TaskStatus.SUCCESS
                self.state.log_decision("Engine", f"Fallback succeeded for '{task.name}'")
                return True
            except Exception as fe:
                logger.error(f"Fallback for '{task.name}' also failed: {fe}")

        task.status = TaskStatus.FAILED
        return False

    def _trigger_rollback(self, completed_tasks: List[str]):
        """LIFO rollback sequence for safe-stop controls."""
        logger.critical(f"Workflow failed. Initiating rollback for {len(completed_tasks)} tasks...")
        self.state.metrics.rollback_frequency += 1

        # Reverse the completion list to rollback in Last-In-First-Out (LIFO) order
        for task_name in reversed(completed_tasks):
            task = self.tasks[task_name]
            if task.rollback:
                logger.info(f"Rolling back: '{task.name}'")
                try:
                    task.rollback(self.state)
                    task.status = TaskStatus.ROLLED_BACK
                except Exception as e:
                    logger.error(f"Rollback failed for '{task.name}': {e}")

    def run(self) -> bool:
        """Executes the DAG using parallel threaded execution and synchronization."""
        logger.info("Starting Stateful Agentic Orchestration Engine (Parallel DAG Mode)...")

        completed_order = []
        in_progress = set()
        pending = {name: task for name, task in self.tasks.items()}

        # Thread pool allows independent parallel agents (e.g. Test Gen & Doc Gen) to run concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}

            while pending or in_progress:
                # 1. Identify tasks whose dependencies are fully resolved
                ready_tasks = []
                for name, task in list(pending.items()):
                    if all(dep in completed_order for dep in task.dependencies):
                        ready_tasks.append(task)

                # 2. Dispatch ready tasks to thread pool
                for task in ready_tasks:
                    pending.pop(task.name)
                    in_progress.add(task.name)
                    futures[executor.submit(self._execute_task_with_retry, task)] = task.name

                # 3. Synchronize and wait for at least one thread to finish
                if futures:
                    done, _ = concurrent.futures.wait(futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED)
                    for fut in done:
                        task_name = futures.pop(fut)
                        in_progress.remove(task_name)
                        success = fut.result()

                        if success:
                            completed_order.append(task_name)
                        else:
                            # 4. Critical failure -> Safe stop and rollback
                            self._trigger_rollback(completed_order)
                            self._finalize_metrics()
                            return False
                elif in_progress:
                    # Waiting on existing tasks to free up downstream dependencies
                    time.sleep(0.5)
                else:
                    # Deadlock detection (Unresolvable dependencies)
                    logger.error("Deadlock detected! Unmet dependencies exist.")
                    self._finalize_metrics()
                    return False

        self._finalize_metrics()
        logger.info(f"Workflow finished in {self.state.metrics.end_to_end_latency}s. Status: SUCCESS")
        return True

    def _finalize_metrics(self):
        self.state.metrics.end_time = time.time()
        self.state.metrics.end_to_end_latency = round(self.state.metrics.end_time - self.state.metrics.start_time, 2)