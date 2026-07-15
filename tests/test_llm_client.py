from neural.baby.llm_client import (
    AVAILABLE_MODELS,
    LLMClient,
    _build_google_generation_config,
)


def test_default_gemini_model_is_stable_and_cost_aligned() -> None:
    config = AVAILABLE_MODELS["gemini-2-flash"]

    assert config.model_id == "gemini-2.5-flash-lite"
    assert config.input_cost_per_1m == 0.10
    assert config.output_cost_per_1m == 0.40


def test_flash_lite_disables_thinking_for_short_chat_budget() -> None:
    config = _build_google_generation_config(
        "gemini-2.5-flash-lite",
        temperature=0.8,
        max_tokens=512,
        thinking_level=None,
    )

    assert config == {
        "temperature": 0.8,
        "max_output_tokens": 512,
        "thinking_config": {"thinking_budget": 0},
    }


def test_gemini_3_thinking_level_is_nested_in_thinking_config() -> None:
    config = _build_google_generation_config(
        "gemini-3.5-flash",
        temperature=0.4,
        max_tokens=1024,
        thinking_level="low",
    )

    assert config["thinking_config"] == {"thinking_level": "low"}


def test_generate_uses_stable_flash_lite_with_zero_thinking_budget() -> None:
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return type("Response", (), {"text": "complete response"})()

    class FakeClient:
        models = FakeModels()

    client = LLMClient()
    client._google_client = FakeClient()

    result = client.generate(
        "컴퓨터는 무엇이야?",
        model_key="gemini-2-flash",
        temperature=0.8,
        max_tokens=512,
    )

    assert result == "complete response"
    assert calls == [{
        "model": "gemini-2.5-flash-lite",
        "contents": "컴퓨터는 무엇이야?",
        "config": {
            "temperature": 0.8,
            "max_output_tokens": 512,
            "thinking_config": {"thinking_budget": 0},
        },
    }]
