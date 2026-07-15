"""Compare legacy and current Gemini Python SDK response metadata.

This probe mirrors the production text-generation request without calling the
conversation endpoint or writing to Neo4j. It intentionally keeps the legacy
SDK available only as an A/B control.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any

from dotenv import load_dotenv

from neural.baby.conversation_handler import _build_system_prompt


DEFAULT_MODEL = "gemini-flash-latest"
DEFAULT_MESSAGE = "컴퓨터는 무엇이야?"


@dataclass
class ProbeResult:
    sdk: str
    model: str
    text: str | None
    finish_reason: str | None
    parts: list[dict[str, Any]]
    usage: dict[str, Any] | None
    error: str | None = None


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    name = getattr(value, "name", None)
    return str(name if name is not None else value)


def _public_values(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def _safe_response_text(response: Any) -> str | None:
    try:
        return response.text
    except (AttributeError, ValueError):
        return None


def _candidate_parts(response: Any) -> tuple[str | None, list[dict[str, Any]]]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None, []

    candidate = candidates[0]
    content = getattr(candidate, "content", None)
    raw_parts = getattr(content, "parts", None) or []
    parts = []
    for part in raw_parts:
        text = getattr(part, "text", None)
        parts.append(
            {
                "text": text,
                "thought": bool(getattr(part, "thought", False)),
            }
        )
    return _enum_value(getattr(candidate, "finish_reason", None)), parts


def _probe_legacy(
    *, api_key: str, model: str, contents: str, temperature: float, max_tokens: int
) -> ProbeResult:
    import google.generativeai as legacy_genai

    try:
        legacy_genai.configure(api_key=api_key)
        response = legacy_genai.GenerativeModel(model).generate_content(
            contents,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        finish_reason, parts = _candidate_parts(response)
        return ProbeResult(
            sdk="google-generativeai",
            model=model,
            text=_safe_response_text(response),
            finish_reason=finish_reason,
            parts=parts,
            usage=_public_values(getattr(response, "usage_metadata", None)),
        )
    except Exception as exc:  # pragma: no cover - live diagnostic path
        return ProbeResult(
            sdk="google-generativeai",
            model=model,
            text=None,
            finish_reason=None,
            parts=[],
            usage=None,
            error=f"{type(exc).__name__}: {exc}",
        )


def _probe_current(
    *,
    api_key: str,
    model: str,
    contents: str,
    temperature: float,
    max_tokens: int,
    thinking_level: str | None = None,
    thinking_budget: int | None = None,
) -> ProbeResult:
    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=api_key)
        thinking_config = None
        if thinking_level is not None or thinking_budget is not None:
            thinking_config = types.ThinkingConfig(
                thinking_level=thinking_level,
                thinking_budget=thinking_budget,
            )
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                thinking_config=thinking_config,
            ),
        )
        finish_reason, parts = _candidate_parts(response)
        return ProbeResult(
            sdk="google-genai",
            model=model,
            text=_safe_response_text(response),
            finish_reason=finish_reason,
            parts=parts,
            usage=_public_values(getattr(response, "usage_metadata", None)),
        )
    except Exception as exc:  # pragma: no cover - live diagnostic path
        return ProbeResult(
            sdk="google-genai",
            model=model,
            text=None,
            finish_reason=None,
            parts=[],
            usage=None,
            error=f"{type(exc).__name__}: {exc}",
        )


def build_probe_contents(message: str) -> str:
    state = {
        "development_stage": 2,
        "dominant_emotion": "curious",
        "curiosity": 0.8,
        "joy": 0.5,
        "fear": 0.1,
        "surprise": 0.3,
        "frustration": 0.1,
        "boredom": 0.1,
    }
    return f"{_build_system_prompt(state)}\n\n{message}"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="A/B Gemini SDKs without creating conversation Experiences"
    )
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument(
        "--sdk",
        choices=("both", "legacy", "current"),
        default="both",
    )
    parser.add_argument(
        "--thinking-level",
        choices=("minimal", "low", "medium", "high"),
    )
    parser.add_argument("--thinking-budget", type=int)
    args = parser.parse_args()

    if args.sdk != "current" and (
        args.thinking_level is not None or args.thinking_budget is not None
    ):
        parser.error("thinking controls require --sdk current")
    if args.thinking_level is not None and args.thinking_budget is not None:
        parser.error("choose either --thinking-level or --thinking-budget")

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GOOGLE_API_KEY is not configured")

    contents = build_probe_contents(args.message)
    results = []
    if args.sdk in {"both", "legacy"}:
        results.append(_probe_legacy(
            api_key=api_key,
            model=args.model,
            contents=contents,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        ))
    if args.sdk in {"both", "current"}:
        results.append(_probe_current(
            api_key=api_key,
            model=args.model,
            contents=contents,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            thinking_level=args.thinking_level,
            thinking_budget=args.thinking_budget,
        ))
    print(
        json.dumps(
            {
                "request": {
                    "message": args.message,
                    "model": args.model,
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "sdk": args.sdk,
                    "thinking_level": args.thinking_level,
                    "thinking_budget": args.thinking_budget,
                    "database_writes": False,
                },
                "results": [asdict(result) for result in results],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if all(result.error for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
