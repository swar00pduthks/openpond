"""
Pipeline abstraction for OpenPond.

Pipelines are ordered sequences of transformation steps that can be
chained together and executed against SmallPond DataFrames, similar to
Databricks Delta Live Tables or Snowflake Tasks.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


class PipelineError(Exception):
    """Raised when a pipeline step fails."""


@dataclass
class StepResult:
    """Result of a single pipeline step execution."""

    name: str
    success: bool
    duration_secs: float
    rows_in: Optional[int] = None
    rows_out: Optional[int] = None
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PipelineResult:
    """Aggregated result of a full pipeline run."""

    pipeline_name: str
    success: bool
    steps: List[StepResult]
    total_duration_secs: float
    started_at: str
    finished_at: str

    @property
    def failed_steps(self) -> List[StepResult]:
        return [s for s in self.steps if not s.success]


class Step:
    """
    A single transformation step in a :class:`Pipeline`.

    A step is a callable that receives the current SmallPond ``DataFrame``
    (or ``None`` for the first step) and returns a new ``DataFrame``.

    Parameters
    ----------
    name:
        Human-readable name for the step.
    func:
        A callable ``(df) -> df`` that transforms the data.
    description:
        Optional description for documentation purposes.
    """

    def __init__(
        self,
        name: str,
        func: Callable[[Any], Any],
        description: str = "",
    ) -> None:
        self.name = name
        self.func = func
        self.description = description

    def __repr__(self) -> str:
        return f"Step(name={self.name!r})"


class Pipeline:
    """
    An ordered sequence of data transformation steps.

    Pipelines are the primary ETL abstraction in OpenPond, inspired by
    Databricks Delta Live Tables and Apache Spark's DataFrame API.

    Example::

        pipeline = (
            Pipeline("daily_sales")
            .add_step("load", lambda _: session.read_parquet("/raw/sales/"))
            .add_step("filter", lambda df: session.partial_sql(
                "SELECT * FROM {0} WHERE amount > 0", df))
            .add_step("save", lambda df: df.write_parquet("/gold/sales/") or df)
        )
        result = pipeline.run()
        print(result.success, result.total_duration_secs)
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._steps: List[Step] = []
        self._on_step_start: Optional[Callable[[str], None]] = None
        self._on_step_end: Optional[Callable[[StepResult], None]] = None

    # ------------------------------------------------------------------
    # Builder API
    # ------------------------------------------------------------------

    def add_step(
        self,
        name: str,
        func: Callable[[Any], Any],
        description: str = "",
    ) -> "Pipeline":
        """Append a transformation step and return ``self`` for chaining."""
        self._steps.append(Step(name=name, func=func, description=description))
        return self

    def on_step_start(self, callback: Callable[[str], None]) -> "Pipeline":
        """Register a callback invoked with the step name before each step."""
        self._on_step_start = callback
        return self

    def on_step_end(self, callback: Callable[[StepResult], None]) -> "Pipeline":
        """Register a callback invoked with the :class:`StepResult` after each step."""
        self._on_step_end = callback
        return self

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, initial_df: Any = None) -> PipelineResult:
        """
        Execute all steps in order.

        Parameters
        ----------
        initial_df:
            Optional starting DataFrame fed into the first step.

        Returns
        -------
        PipelineResult
            Contains per-step results and overall success/failure status.
        """
        start = time.time()
        started_at = datetime.now(timezone.utc).isoformat()
        step_results: List[StepResult] = []
        current_df = initial_df
        overall_success = True

        for step in self._steps:
            if self._on_step_start:
                self._on_step_start(step.name)

            step_start = time.time()
            step_result = StepResult(name=step.name, success=False, duration_secs=0.0)
            try:
                rows_in = None
                try:
                    if current_df is not None:
                        rows_in = current_df.count()
                except Exception:
                    pass

                current_df = step.func(current_df)

                rows_out = None
                try:
                    if current_df is not None:
                        rows_out = current_df.count()
                except Exception:
                    pass

                step_result = StepResult(
                    name=step.name,
                    success=True,
                    duration_secs=time.time() - step_start,
                    rows_in=rows_in,
                    rows_out=rows_out,
                )
            except Exception:  # noqa: BLE001
                import traceback

                step_result = StepResult(
                    name=step.name,
                    success=False,
                    duration_secs=time.time() - step_start,
                    error=traceback.format_exc(),
                )
                overall_success = False

            step_results.append(step_result)
            if self._on_step_end:
                self._on_step_end(step_result)

            if not step_result.success:
                break

        return PipelineResult(
            pipeline_name=self.name,
            success=overall_success,
            steps=step_results,
            total_duration_secs=time.time() - start,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        step_names = " -> ".join(s.name for s in self._steps)
        return f"Pipeline(name={self.name!r}, steps=[{step_names}])"

    def steps(self) -> List[Step]:
        """Return the list of steps (read-only copy)."""
        return list(self._steps)
