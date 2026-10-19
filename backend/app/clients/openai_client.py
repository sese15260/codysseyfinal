"""OpenAI-compatible provider boundary for generated answer explanations."""

import json
from typing import Any

from openai import OpenAI

from app.core.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


class AIProviderError(RuntimeError):
    """A provider or provider-output failure safe to map to a generic 502."""


_INSTRUCTIONS = """
당신은 TOEIC 학습 해설 도우미입니다. 반드시 제공된 retrieval context를 최우선 근거로
사용하세요. context에 없는 문법 규칙·사실·함정은 확신해서 만들어내지 마세요.
학습자의 실제 선택지와 정답을 비교해 자연스러운 한국어로 간결하게 설명하세요.
사용자가 맞힌 경우 selected_choice_reason에는 왜 그 선택이 올바른지도 설명하세요.
오답 함정 정보가 있는 경우에만 trap에 그 함정을 연결하세요.

응답은 Markdown이나 코드 블록 없이 다음 JSON 객체만 반환해야 합니다.
{
  "summary": "짧은 요약",
  "correct_reason": "정답 근거",
  "selected_choice_reason": "사용자 선택 설명",
  "trap": {"code": "TR-01", "name": "함정명", "explanation": "함정 설명"} 또는 null,
  "rule": "이 문제에 적용되는 제공된 규칙 또는 단서",
  "next_tip": "다음 문제를 위한 구체적인 한 가지 팁"
}
모든 문자열은 빈 문자열이 아니어야 합니다.
""".strip()


def generate_explanation(context: dict[str, Any]) -> str:
    """Generate JSON text with Chat Completions, without a hidden fallback."""
    if not OPENAI_API_KEY or not OPENAI_MODEL:
        raise AIProviderError("AI provider is not configured.")

    client_options: dict[str, str] = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        client_options["base_url"] = OPENAI_BASE_URL

    try:
        client = OpenAI(**client_options)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _INSTRUCTIONS},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
        )
        output_text = response.choices[0].message.content if response.choices else None
    except Exception as error:
        raise AIProviderError("AI provider request failed.") from error

    if not output_text or not output_text.strip():
        raise AIProviderError("AI provider returned an empty response.")

    return output_text
