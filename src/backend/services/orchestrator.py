"""
===============================================================================
File: orchestrator.py
Description: Manages background tasks for continuous fetching of external API data.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import asyncio
import logging
from typing import Awaitable, Callable, List, Tuple

logger = logging.getLogger(__name__)


class BackgroundOrchestrator:
    """
    Manages isolated background tasks that run at regular intervals.
    Each registered task runs in its own asyncio loop, ensuring that a failure
    or hang in one task does not affect the others.
    """

    def __init__(self):
        self._tasks: List[asyncio.Task] = []
        self._registered_funcs: List[
            Tuple[str, Callable[[], Awaitable[None]], int]
        ] = []

    def register(
        self, name: str, func: Callable[[], Awaitable[None]], interval_seconds: int
    ):
        """Registers an asynchronous function to be run repeatedly."""
        self._registered_funcs.append((name, func, interval_seconds))
        logger.info(
            f"Registered background task '{name}' (Interval: {interval_seconds}s)"
        )

    async def start(self):
        """Starts all registered background tasks in isolated loops."""
        logger.info("Starting background orchestrator...")
        for name, func, interval in self._registered_funcs:
            task = asyncio.create_task(self._run_task(name, func, interval))
            self._tasks.append(task)

    async def stop(self):
        """Cancels all running background tasks and waits for them to exit."""
        logger.info("Stopping background orchestrator...")
        for task in self._tasks:
            task.cancel()

        # Wait for all tasks to acknowledge cancellation
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run_task(
        self, name: str, func: Callable[[], Awaitable[None]], interval: int
    ):
        """The isolated runner loop for a single task."""
        # Initial run immediately on startup
        try:
            await func()
        except Exception:
            logger.exception(f"Initial run failed for task: {name}")

        # Infinite loop for subsequent runs
        while True:
            await asyncio.sleep(interval)
            try:
                await func()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(f"Error in background task: {name}")
