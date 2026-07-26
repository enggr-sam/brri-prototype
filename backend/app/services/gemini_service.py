"""Google Gemini integration — streaming chat, cost tracking, concise replies."""

from __future__ import annotations

import logging
import mimetypes
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.knowledge_base import KnowledgeBase, get_knowledge_base
from app.services.reference_selector import (
    build_image_selection_query,
    user_requests_visual_help,
    _issue_matched_numbers,
)
from app.utils.parts_suppliers import ensure_belt_supplier_reply, is_belt_supplier_query
from app.utils.cost_estimator import estimate_cost_usd, extract_usage
from app.utils.image_captions import caption_prompt, parse_image_caption_lines
from app.utils.reply_metadata import META_MARKER, split_reply_metadata

logger = logging.getLogger(__name__)

_NO_KEY_MESSAGE = (
    "দুঃখিত, এই মুহূর্তে AI সহায়তা সেবাটি কনফিগার করা হয়নি। "
    "অনুগ্রহ করে সার্ভারের `.env` ফাইলে একটি বৈধ `GEMINI_API_KEY` যুক্ত করুন।"
)

_META_PREFIXES = ("---", "---M", "---ME", "---MET", "---META")


def _resolve_show_reference_images(
    user_text: str,
    reference_images: list[Path],
    meta: dict,
    history: list[dict[str, str]] | None = None,
) -> bool:
    """Decide whether to show the reference gallery in the UI."""
    if not reference_images:
        return False
    if is_belt_supplier_query(user_text):
        return False
    if user_requests_visual_help(user_text):
        return True
    query = build_image_selection_query(user_text, history)
    if _issue_matched_numbers(query):
        return True
    if meta.get("show_images") is True:
        return True
    if meta.get("show_images") is False:
        return False
    return True


class QuotaExceededError(Exception):
    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class UsageCost:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model_used: str = ""


@dataclass
class ChatReplyResult:
    text: str
    image_captions: dict[int, str] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    show_reference_images: bool = False
    usage: UsageCost = field(default_factory=UsageCost)


def _is_quota_error(exc: Exception) -> bool:
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status == 429:
        return True
    text = str(exc).upper()
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def _should_fallback(exc: Exception) -> bool:
    if _is_quota_error(exc):
        return True
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status in (404, 503):
        return True
    text = str(exc).upper()
    return "NOT_FOUND" in text or "UNAVAILABLE" in text


_AUDIO_EXT_MIME = {
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/ogg",
    ".mp3": "audio/mp3",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".aac": "audio/aac",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
}


def _resolve_audio_mime(path: Path, provided: str | None) -> str:
    if provided:
        base = provided.split(";")[0].strip().lower()
        if base.startswith("audio/"):
            return base
    return _AUDIO_EXT_MIME.get(path.suffix.lower(), "audio/webm")


def _retry_after_seconds(exc: Exception | None) -> int | None:
    if exc is None:
        return None
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc))
    if match:
        return int(float(match.group(1))) + 1
    return None


def _safe_visible_suffix(buffer: str) -> str:
    """Hold back text that might be the start of ---META---."""
    for prefix in reversed(_META_PREFIXES):
        if buffer.endswith(prefix):
            return buffer[: -len(prefix)]
    return buffer


class GeminiService:
    def __init__(self) -> None:
        self._client = None
        self._types = None
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                from google.genai import types

                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self._types = types
                logger.info("Gemini client initialised (model=%s).", settings.GEMINI_MODEL)
            except Exception as exc:
                logger.exception("Failed to initialise Gemini client: %s", exc)
        else:
            logger.warning("GEMINI_API_KEY not set; running in offline/demo mode.")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def _image_part(self, path: Path):
        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "image/jpeg"
        return self._types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)

    def _reference_image_parts(self, reference_images: list[Path]) -> list:
        kb = get_knowledge_base()
        parts: list = []
        for img in reference_images:
            entry = kb._by_name.get(img.name, {})
            num = entry.get("image_number")
            desc = entry.get("description") or ""
            if "Troubleshooting context:" in desc:
                short = desc.split("Troubleshooting context:", 1)[-1].strip()
            else:
                short = desc[:100].strip()
            label = f"[Reference #{num}: {img.name}]"
            if short:
                label += f"\n{short[:120]}"
            parts.append(self._types.Part.from_text(text=label))
            parts.append(self._image_part(img))
        return parts

    def _chat_generation_config(self, kb: KnowledgeBase):
        return self._types.GenerateContentConfig(
            system_instruction=kb.build_system_instruction(),
            max_output_tokens=768,
            temperature=0.35,
        )

    def _caption_generation_config(self, kb: KnowledgeBase):
        return self._types.GenerateContentConfig(
            system_instruction=kb.build_system_instruction(),
            max_output_tokens=512,
            temperature=0.3,
        )

    def _usage_from_response(self, response, model: str) -> UsageCost:
        inp, out = extract_usage(response)
        return UsageCost(
            input_tokens=inp,
            output_tokens=out,
            cost_usd=estimate_cost_usd(model, inp, out),
            model_used=model,
        )

    def _generate_with_fallback(self, contents: list, config=None) -> tuple[str, UsageCost]:
        last_exc: Exception | None = None
        for model in settings.model_chain:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                text = (response.text or "").strip()
                if not text:
                    candidates = getattr(response, "candidates", None) or []
                    if candidates:
                        content = getattr(candidates[0], "content", None)
                        if content and getattr(content, "parts", None):
                            text = "".join(
                                getattr(p, "text", "") or "" for p in content.parts
                            ).strip()
                if model != settings.GEMINI_MODEL:
                    logger.warning("Primary model failed; used fallback %s.", model)
                return text, self._usage_from_response(response, model)
            except Exception as exc:
                if _should_fallback(exc):
                    logger.warning("Model %s unavailable, trying next: %s", model, str(exc)[:120])
                    last_exc = exc
                    continue
                raise
        raise QuotaExceededError(
            "All configured Gemini models are unavailable or quota-exhausted.",
            retry_after=_retry_after_seconds(last_exc),
        )

    def _stream_generate_with_fallback(
        self, contents: list, config=None
    ) -> tuple[str, UsageCost]:
        last_exc: Exception | None = None
        for model in settings.model_chain:
            try:
                buffer = ""
                usage = UsageCost(model_used=model)
                stream = self._client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config,
                )
                for chunk in stream:
                    inp, out = extract_usage(chunk)
                    if inp or out:
                        usage.input_tokens = max(usage.input_tokens, inp)
                        usage.output_tokens = max(usage.output_tokens, out)
                    if chunk.text:
                        buffer += chunk.text
                usage.cost_usd = estimate_cost_usd(
                    model, usage.input_tokens, usage.output_tokens
                )
                if model != settings.GEMINI_MODEL:
                    logger.warning("Primary model failed; used fallback %s.", model)
                return buffer.strip(), usage
            except Exception as exc:
                if _should_fallback(exc):
                    logger.warning("Model %s unavailable, trying next: %s", model, str(exc)[:120])
                    last_exc = exc
                    continue
                raise
        raise QuotaExceededError(
            "All configured Gemini models are unavailable or quota-exhausted.",
            retry_after=_retry_after_seconds(last_exc),
        )

    def stream_visible_tokens(
        self,
        history: list[dict[str, str]],
        user_text: str,
        reference_images: list[Path],
        user_image_path: Path | None = None,
    ) -> Iterator[str]:
        """Yield visible reply tokens only (stops before ---META--- block)."""
        kb = get_knowledge_base()
        if not self.is_configured:
            yield _NO_KEY_MESSAGE
            return

        contents = self._build_chat_contents(
            history, user_text, reference_images, user_image_path
        )

        last_exc: Exception | None = None
        for model in settings.model_chain:
            try:
                buffer = ""
                sent_len = 0
                usage = UsageCost(model_used=model)
                stream = self._client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=self._chat_generation_config(kb),
                )
                for chunk in stream:
                    inp, out = extract_usage(chunk)
                    if inp:
                        usage.input_tokens = max(usage.input_tokens, inp)
                    if out:
                        usage.output_tokens = max(usage.output_tokens, out)
                    if not chunk.text:
                        continue
                    buffer += chunk.text
                    if META_MARKER in buffer:
                        visible = buffer.split(META_MARKER, 1)[0]
                        new_text = visible[sent_len:]
                        if new_text:
                            yield new_text
                        sent_len = len(visible)
                        break
                    safe = _safe_visible_suffix(buffer)
                    new_text = safe[sent_len:]
                    if new_text:
                        yield new_text
                    sent_len = len(safe)
                usage.cost_usd = estimate_cost_usd(
                    model, usage.input_tokens, usage.output_tokens
                )
                self._last_stream_buffer = buffer
                self._last_stream_model = model
                self._last_stream_usage = usage
                return
            except Exception as exc:
                if _should_fallback(exc):
                    last_exc = exc
                    continue
                raise
        raise QuotaExceededError(
            "All configured Gemini models are unavailable or quota-exhausted.",
            retry_after=_retry_after_seconds(last_exc),
        )

    def finalize_streamed_reply(
        self,
        user_text: str,
        reference_images: list[Path],
        history: list[dict[str, str]] | None = None,
    ) -> ChatReplyResult:
        """Parse streamed buffer, captions, usage — call after stream completes."""
        from app.utils.response_filter import filter_assistant_reply

        raw = getattr(self, "_last_stream_buffer", "") or ""
        usage = getattr(self, "_last_stream_usage", None) or UsageCost(
            model_used=getattr(self, "_last_stream_model", settings.GEMINI_MODEL)
        )

        main_raw, meta = split_reply_metadata(raw)
        main_text = filter_assistant_reply(main_raw)
        main_text = ensure_belt_supplier_reply(main_text, user_text)
        show_images = _resolve_show_reference_images(
            user_text, reference_images, meta, history
        )
        suggestions = meta.get("suggestions") or []

        captions: dict[int, str] = {}
        if show_images and reference_images:
            cap_raw, cap_usage = self._generate_with_fallback(
                [
                    self._types.Part.from_text(
                        text=caption_prompt(user_text, main_text, reference_images)
                    )
                ],
                config=self._caption_generation_config(get_knowledge_base()),
            )
            captions = parse_image_caption_lines(cap_raw)
            usage.input_tokens += cap_usage.input_tokens
            usage.output_tokens += cap_usage.output_tokens
            usage.cost_usd = round(usage.cost_usd + cap_usage.cost_usd, 6)

        return ChatReplyResult(
            text=main_text,
            image_captions=captions if show_images else {},
            suggestions=suggestions[:3],
            show_reference_images=show_images,
            usage=usage,
        )

    def _build_chat_contents(
        self,
        history: list[dict[str, str]],
        user_text: str,
        reference_images: list[Path],
        user_image_path: Path | None,
    ) -> list:
        types = self._types
        contents: list = []
        if reference_images:
            contents.extend(self._reference_image_parts(reference_images))

        if user_image_path is not None:
            contents.append(
                types.Part.from_text(
                    text="[User uploaded a NEW photo of the part that may be faulty:]"
                )
            )
            contents.append(self._image_part(user_image_path))

        history_block = self._format_history(history)
        prompt_parts = []
        if history_block:
            prompt_parts.append("Previous conversation:\n" + history_block)
        prompt_parts.append(f"Current user message:\n{user_text.strip()}")
        prompt_parts.append(
            "Reply in concise natural Bangla. Follow prompts.txt format rules. "
            "Append ---META--- block as instructed."
        )
        contents.append(types.Part.from_text(text="\n\n".join(prompt_parts)))
        return contents

    def chat_reply(
        self,
        history: list[dict[str, str]],
        user_text: str,
        reference_images: list[Path],
        user_image_path: Path | None = None,
    ) -> ChatReplyResult:
        from app.utils.response_filter import filter_assistant_reply

        kb = get_knowledge_base()
        if not self.is_configured:
            return ChatReplyResult(text=_NO_KEY_MESSAGE)

        contents = self._build_chat_contents(
            history, user_text, reference_images, user_image_path
        )

        try:
            raw, usage = self._stream_generate_with_fallback(
                contents, config=self._chat_generation_config(kb)
            )
            main_raw, meta = split_reply_metadata(raw)
            main_text = filter_assistant_reply(main_raw)
            main_text = ensure_belt_supplier_reply(main_text, user_text)
            show_images = _resolve_show_reference_images(
                user_text, reference_images, meta, history
            )
            suggestions = meta.get("suggestions") or []

            captions: dict[int, str] = {}
            if show_images and reference_images:
                cap_raw, cap_usage = self._generate_with_fallback(
                    [
                        self._types.Part.from_text(
                            text=caption_prompt(user_text, main_text, reference_images)
                        )
                    ],
                    config=self._caption_generation_config(kb),
                )
                captions = parse_image_caption_lines(cap_raw)
                usage.input_tokens += cap_usage.input_tokens
                usage.output_tokens += cap_usage.output_tokens
                usage.cost_usd = round(usage.cost_usd + cap_usage.cost_usd, 6)

            return ChatReplyResult(
                text=main_text,
                image_captions=captions if show_images else {},
                suggestions=suggestions[:3],
                show_reference_images=show_images,
                usage=usage,
            )
        except Exception as exc:
            logger.exception("Chat request failed: %s", exc)
            raise

    @staticmethod
    def _format_history(history: list[dict[str, str]], limit: int = 6) -> str:
        lines: list[str] = []
        for msg in history[-limit:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = (msg.get("content") or "").strip()
            if len(content) > 200:
                content = content[:200].rstrip() + "…"
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def transcribe_audio(self, audio_path: Path, content_type: str | None = None) -> str:
        if not self.is_configured:
            return ""
        mime = _resolve_audio_mime(audio_path, content_type)
        audio_part = self._types.Part.from_bytes(
            data=audio_path.read_bytes(), mime_type=mime
        )
        prompt = self._types.Part.from_text(
            text=(
                "Transcribe the following audio verbatim. The speaker is most "
                "likely describing a problem with an agricultural winnower "
                "machine, possibly in Bengali. Return ONLY the transcription text."
            )
        )
        text, _ = self._generate_with_fallback([prompt, audio_part])
        return text


gemini_service = GeminiService()
