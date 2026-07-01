"""Thin async client around the DeepSeek (OpenAI-compatible) chat API."""

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# A tool executor takes (tool_name, arguments) and returns a JSON-serializable result.
ToolExecutor = Callable[[str, dict], Awaitable[object]]


@dataclass
class ChatResult:
    """Outcome of a chat completion call."""

    content: str
    tokens_prompt: int | None
    tokens_completion: int | None


class DeepSeekClient:
    """Wraps the OpenAI SDK pointed at the DeepSeek endpoint."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self._model = settings.deepseek_model

    async def chat(self, messages: list[dict]) -> ChatResult:
        """Send a list of {role, content} messages and return the reply."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
        )
        choice = response.choices[0]
        usage = response.usage
        return ChatResult(
            content=choice.message.content or "",
            tokens_prompt=usage.prompt_tokens if usage else None,
            tokens_completion=usage.completion_tokens if usage else None,
        )

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_executor: ToolExecutor,
        max_rounds: int = 3,
    ) -> ChatResult:
        """Run a tool-calling loop until the model returns a final answer.

        The model may request tool calls; we execute them via ``tool_executor``,
        feed the results back, and repeat up to ``max_rounds`` times.
        """
        working = list(messages)
        prompt_tokens = 0
        completion_tokens = 0

        for _ in range(max_rounds):
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=working,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type]
                tool_choice="auto",
            )
            if response.usage:
                prompt_tokens += response.usage.prompt_tokens
                completion_tokens += response.usage.completion_tokens

            message = response.choices[0].message
            if not message.tool_calls:
                return ChatResult(
                    content=message.content or "",
                    tokens_prompt=prompt_tokens,
                    tokens_completion=completion_tokens,
                )

            # Record the assistant's tool-call request, then answer each call.
            working.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    result = await tool_executor(tc.function.name, args)
                except Exception as exc:  # noqa: BLE001 - report tool errors to the model
                    logger.exception("tool execution failed: %s", tc.function.name)
                    result = {"error": str(exc)}
                working.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        # Ran out of rounds: ask once more without tools for a final answer.
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=working,  # type: ignore[arg-type]
        )
        if response.usage:
            prompt_tokens += response.usage.prompt_tokens
            completion_tokens += response.usage.completion_tokens
        return ChatResult(
            content=response.choices[0].message.content or "",
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
        )


# Module-level singleton (the SDK client is safe to reuse).
deepseek_client = DeepSeekClient()
