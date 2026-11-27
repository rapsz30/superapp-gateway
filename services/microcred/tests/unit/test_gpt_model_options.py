from __future__ import annotations

import pytest
from src.libs.gpt_client import model_options


@pytest.mark.parametrize("model", ["gpt-4o-mini", "gpt-4.1"])
def test_older_models_use_max_tokens(model: str) -> None:
    assert model_options(model, 500) == {"max_tokens": 500}


@pytest.mark.parametrize("model", ["gpt-6-luna", "gpt-5", "gpt-10", "o3-mini"])
def test_newer_models_use_completion_tokens_without_reasoning(model: str) -> None:
    assert model_options(model, 500) == {
        "max_completion_tokens": 1000,
        "reasoning_effort": "none",
    }
