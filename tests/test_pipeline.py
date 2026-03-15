"""Tests for the Pipeline class."""

import pytest

from openpond.pipeline import Pipeline, PipelineError, StepResult


# ---------------------------------------------------------------------------
# Basic pipeline execution
# ---------------------------------------------------------------------------


class TestPipelineExecution:
    def test_single_step(self):
        pipeline = Pipeline("test")
        pipeline.add_step("double", lambda x: (x or 0) * 2)
        result = pipeline.run(initial_df=5)
        assert result.success
        assert len(result.steps) == 1
        assert result.steps[0].success
        assert result.steps[0].name == "double"

    def test_chained_steps(self):
        results = []
        pipeline = (
            Pipeline("chain")
            .add_step("step1", lambda _: 10)
            .add_step("step2", lambda x: x + 5)
            .add_step("step3", lambda x: x * 2)
        )
        result = pipeline.run()
        assert result.success
        assert len(result.steps) == 3

    def test_failing_step_stops_pipeline(self):
        def boom(_):
            raise ValueError("oops")

        pipeline = (
            Pipeline("failing")
            .add_step("ok", lambda _: 1)
            .add_step("fail", boom)
            .add_step("never_reached", lambda x: x)
        )
        result = pipeline.run()
        assert not result.success
        assert len(result.steps) == 2  # third step never ran
        assert result.steps[1].error == "oops"
        assert len(result.failed_steps) == 1

    def test_pipeline_result_metadata(self):
        pipeline = Pipeline("meta", description="test pipeline")
        pipeline.add_step("noop", lambda _: None)
        result = pipeline.run()
        assert result.pipeline_name == "meta"
        assert result.total_duration_secs >= 0
        assert result.started_at
        assert result.finished_at

    def test_on_step_callbacks(self):
        started = []
        ended = []

        pipeline = (
            Pipeline("callbacks")
            .on_step_start(lambda name: started.append(name))
            .on_step_end(lambda r: ended.append(r.name))
            .add_step("a", lambda _: 1)
            .add_step("b", lambda x: x + 1)
        )
        pipeline.run()
        assert started == ["a", "b"]
        assert ended == ["a", "b"]

    def test_builder_returns_self(self):
        p = Pipeline("builder")
        result = p.add_step("s", lambda _: None)
        assert result is p

    def test_repr(self):
        p = Pipeline("my_pipe").add_step("s1", lambda _: None).add_step("s2", lambda _: None)
        r = repr(p)
        assert "my_pipe" in r
        assert "s1" in r
        assert "s2" in r

    def test_steps_returns_copy(self):
        p = Pipeline("p").add_step("s", lambda _: None)
        steps = p.steps()
        steps.clear()
        assert len(p.steps()) == 1
