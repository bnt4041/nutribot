"""Thin async client around the DeepSeek (OpenAI-compatible) chat API."""

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services.deepseek.hallucination_guard import looks_like_unbacked_action_claim
from app.services.deepseek.leaked_tools import parse_leaked_tool_calls

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
        max_rounds: int = 6,
        initial_tool_choice: str | dict = "auto",
    ) -> ChatResult:
        """Run a tool-calling loop until the model returns a final answer.

        The model may request tool calls; we execute them via ``tool_executor``,
        feed the results back, and repeat up to ``max_rounds`` times.
        ``initial_tool_choice`` forces the first round's choice (e.g. pin a
        specific function when the caller already knows it must run); every
        later round falls back to "auto".
        """
        working = list(messages)
        prompt_tokens = 0
        completion_tokens = 0
        any_tool_called = False
        next_tool_choice = initial_tool_choice

        for _ in range(max_rounds):
            tool_choice = next_tool_choice
            next_tool_choice = "auto"
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=working,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type]
                tool_choice=tool_choice,
            )
            if response.usage:
                prompt_tokens += response.usage.prompt_tokens
                completion_tokens += response.usage.completion_tokens

            message = response.choices[0].message

            # Normalize native tool calls and any the model leaked as plain text
            # into a common (id, name, arguments_json) shape. DeepSeek V3 sometimes
            # writes the call as DSML/antml markup in ``content`` instead of using
            # the function-calling protocol; recover those so the action still runs.
            calls: list[tuple[str, str, str]] = []
            assistant_content = message.content or ""
            if message.tool_calls:
                calls = [
                    (tc.id, tc.function.name, tc.function.arguments or "{}")
                    for tc in message.tool_calls
                ]
            else:
                leaked = parse_leaked_tool_calls(assistant_content)
                if leaked:
                    logger.warning(
                        "recovered %d leaked tool call(s) from message content",
                        len(leaked),
                    )
                    calls = [
                        (f"leaked_{i}", name, json.dumps(args))
                        for i, (name, args) in enumerate(leaked)
                    ]
                    # Drop the raw markup so it never re-enters the conversation.
                    assistant_content = ""

            if not calls:
                # The model may narrate a fake tool call in plain prose ("Voy a
                # actualizar... Hecho ✅") without invoking any function, native
                # or leaked. Only distrust this when NO tool has run at all this
                # turn — once a real call has executed earlier in the loop, a
                # later "confirmada"-style wrap-up is the legitimate final answer.
                # Asking nicely once already failed in production (the model
                # repeated the same fabricated narration), so force the issue
                # structurally: tool_choice="required" makes the API itself
                # guarantee a real function call on the next round.
                if not any_tool_called and looks_like_unbacked_action_claim(
                    assistant_content
                ):
                    logger.warning(
                        "discarding unbacked action claim, forcing tool_choice=required"
                    )
                    next_tool_choice = "required"
                    working.append(
                        {
                            "role": "system",
                            "content": (
                                "Tu último mensaje describía una acción (confirmar, "
                                "actualizar, guardar, añadir o eliminar algo) pero no "
                                "llamaste a ninguna función. No expliques pasos "
                                "internos ni des por hecho un cambio: invoca ahora "
                                "mismo la herramienta real correspondiente."
                            ),
                        }
                    )
                    continue
                return ChatResult(
                    content=assistant_content,
                    tokens_prompt=prompt_tokens,
                    tokens_completion=completion_tokens,
                )

            # Record the assistant's tool-call request, then answer each call.
            any_tool_called = True
            working.append(
                {
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": [
                        {
                            "id": cid,
                            "type": "function",
                            "function": {"name": name, "arguments": args_json},
                        }
                        for cid, name, args_json in calls
                    ],
                }
            )
            for cid, name, args_json in calls:
                try:
                    args = json.loads(args_json or "{}")
                    result = await tool_executor(name, args)
                except Exception as exc:  # noqa: BLE001 - report tool errors to the model
                    logger.exception("tool execution failed: %s", name)
                    result = {"error": str(exc)}
                working.append(
                    {
                        "role": "tool",
                        "tool_call_id": cid,
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


    async def chat_raw(self, messages: list[dict]) -> ChatResult:
        """Send arbitrary messages (including image content blocks) without tools.

        The ``messages`` list may contain dicts with ``content`` as a list of
        content blocks (text + image_url), as in the OpenAI vision API.
        """
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


# Module-level singleton (the SDK client is safe to reuse).
deepseek_client = DeepSeekClient()
