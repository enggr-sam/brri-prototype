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
from app.utils.conversation_focus import (
    build_conversation_focus,
    conversation_wants_visuals,
)
from app.utils.image_reasoner import (
    build_image_reason_prompt,
    parse_image_reason_response,
)
from app.services.reference_selector import (
    retrieve_scored_candidates,
    select_reference_images,
    user_requests_visual_help,
    build_grounding_context,
)
from app.utils.canonical_replies import ensure_canonical_reply, is_off_topic_refusal
from app.utils.fast_path import FastPathHit, try_fast_path
from app.utils.parts_suppliers import (
    ensure_belt_dealers_in_reply,
    is_belt_price_query,
    is_belt_supplier_query,
)
from app.utils.cost_estimator import estimate_cost_usd, extract_usage
from app.utils.follow_ups import local_suggestions
from app.utils.image_captions import caption_prompt, parse_image_caption_lines
from app.utils.reply_metadata import META_MARKER, split_reply_metadata
from app.utils.reply_polish import needs_polish, polish_prompt
from app.utils.response_filter import filter_assistant_reply, strip_gallery_pointers

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
    reply_text: str = "",
) -> bool:
    """Decide whether to show the reference gallery in the UI."""
    if not reference_images:
        return False
    if is_off_topic_refusal(reply_text):
        return False
    if is_belt_supplier_query(user_text):
        return False
    if is_belt_price_query(user_text, history):
        return False
    if conversation_wants_visuals(user_text, history):
        return True
    if user_requests_visual_help(user_text):
        return True
    if meta.get("show_images") is True:
        return True
    if meta.get("show_images") is False:
        return False
    # Only the on-topic shortlist is passed in — show it.
    return True


def _ranking_is_decisive(scored: list[tuple[float, dict]]) -> bool:
    """True when the shortlist needs no LLM arbitration.

    Either there is nothing to choose between, or the winners are far enough ahead of
    the first image we would not show that the reasoner cannot change the outcome.
    """
    limit = settings.MAX_REFERENCE_IMAGES
    if len(scored) <= limit:
        return True
    margin = settings.IMAGE_REASONER_SKIP_MARGIN
    if margin <= 0:
        return False
    worst_kept = scored[limit - 1][0]
    best_dropped = scored[limit][0]
    if best_dropped <= 0:
        return True
    return worst_kept >= best_dropped * margin


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

    def pick_reference_images(
        self,
        user_text: str,
        history: list[dict[str, str]] | None = None,
        *,
        has_user_image: bool = False,
    ) -> list[Path]:
        """Focus → retrieve shortlist → reason which images fit → return paths."""
        scored = retrieve_scored_candidates(user_text, history)
        if not scored:
            return []

        candidates = [c for _, c in scored]
        preferred: list[int] = []
        wants = conversation_wants_visuals(user_text, history) or has_user_image
        focus = build_conversation_focus(user_text, history)
        allowed = {
            int(c["image_number"])
            for c in candidates
            if c.get("image_number") is not None
        }

        if not settings.ENABLE_IMAGE_REASONER:
            logger.debug("Image reasoner disabled; using ranked shortlist.")
        elif _ranking_is_decisive(scored):
            logger.info(
                "Ranking decisive (%s); skipped image reasoner call.",
                [(c.get("image_number"), round(s, 1)) for s, c in scored[:3]],
            )
        elif self.is_configured and candidates:
            try:
                prompt = build_image_reason_prompt(
                    focus, user_text, candidates, wants_photos=wants
                )
                raw, _usage = self._generate_with_fallback(
                    [self._types.Part.from_text(text=prompt)],
                    config=self._types.GenerateContentConfig(
                        system_instruction=(
                            "You are a careful image picker for BRRI Winnower support. "
                            "Match photos to the conversation topic only. JSON only."
                        ),
                        max_output_tokens=256,
                        temperature=0.1,
                    ),
                    fast=True,
                )
                preferred = parse_image_reason_response(raw, allowed)
                logger.info(
                    "Image reasoner focus=%r wants_photos=%s picked=%s",
                    focus[:80],
                    wants,
                    preferred,
                )
            except Exception:
                logger.exception("Image reasoner failed; using ranked shortlist.")

        return select_reference_images(
            user_text=user_text,
            has_user_image=has_user_image,
            history=history,
            preferred_numbers=preferred or None,
        )

    def _catalog_images_for_gemini(
        self,
        reference_images: list[Path],
        user_image_path: Path | None,
    ) -> list[Path]:
        """On-topic gallery JPEGs sent to Gemini (same photos the farmer sees)."""
        refs = list(reference_images or [])
        if not refs or not settings.ATTACH_CATALOG_IMAGES_TO_GEMINI:
            return []
        # Symptom turns already cap at 2; never dump the whole catalogue.
        return refs[:2]

    @staticmethod
    def _result_from_fast_path(hit: FastPathHit) -> ChatReplyResult:
        return ChatReplyResult(
            text=hit.text,
            suggestions=hit.suggestions[:3],
            show_reference_images=hit.show_reference_images,
        )

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
            label = f"[Reference #{num}: {img.name} — also shown in the app gallery]"
            if short:
                label += f"\n{short[:120]}"
            parts.append(self._types.Part.from_text(text=label))
            parts.append(self._image_part(img))
        return parts

    def _chat_generation_config(self, kb: KnowledgeBase):
        return self._types.GenerateContentConfig(
            system_instruction=kb.build_system_instruction(),
            max_output_tokens=1536,
            temperature=0.35,
        )

    def _polish_generation_config(self, kb: KnowledgeBase):
        return self._types.GenerateContentConfig(
            system_instruction=kb.build_editor_instruction(),
            max_output_tokens=1024,
            temperature=0.2,
        )

    def _caption_generation_config(self, kb: KnowledgeBase):
        return self._types.GenerateContentConfig(
            system_instruction=kb.build_caption_instruction(),
            max_output_tokens=512,
            temperature=0.3,
        )

    def _polish_draft(
        self,
        user_text: str,
        draft: str,
        usage: UsageCost,
    ) -> tuple[str, dict, UsageCost]:
        """Analyze question + draft → complete concise Bangla answer + META."""
        kb = get_knowledge_base()
        draft_clean = filter_assistant_reply(draft)
        force = needs_polish(draft_clean)
        if not force and settings.POLISH_ONLY_WHEN_NEEDED:
            # Draft is already complete — skip a whole model call.
            main, meta = split_reply_metadata(draft_clean)
            main = filter_assistant_reply(main)
            if main:
                logger.info("Draft complete; skipped polish call (%d chars).", len(main))
                return main, meta if meta else {}, usage
        try:
            polished_raw, polish_usage = self._generate_with_fallback(
                [self._types.Part.from_text(text=polish_prompt(user_text, draft_clean))],
                config=self._polish_generation_config(kb),
            )
            usage.input_tokens += polish_usage.input_tokens
            usage.output_tokens += polish_usage.output_tokens
            usage.cost_usd = round(usage.cost_usd + polish_usage.cost_usd, 6)
            if polish_usage.model_used and not usage.model_used:
                usage.model_used = polish_usage.model_used

            main, meta = split_reply_metadata(polished_raw)
            main = filter_assistant_reply(main)
            if main and not needs_polish(main):
                logger.info(
                    "Polished reply OK (draft_chars=%d → final_chars=%d).",
                    len(draft_clean),
                    len(main),
                )
                return main, meta, usage
            # Prefer a longer polished attempt when the draft was clearly broken.
            if (
                main
                and force
                and len(main) >= max(40, len(draft_clean) + 10)
            ):
                logger.info("Using polished reply over truncated draft.")
                return main, meta, usage
            logger.warning("Polish still incomplete; keeping cleaned draft.")
        except Exception:
            logger.exception("Reply polish failed; using draft.")

        main, meta = split_reply_metadata(draft_clean)
        main = filter_assistant_reply(main)
        return main, meta if meta else {}, usage

    def _assemble_chat_result(
        self,
        user_text: str,
        draft: str,
        reference_images: list[Path],
        history: list[dict[str, str]] | None,
        usage: UsageCost,
    ) -> ChatReplyResult:
        """Polish Q+A, inject dealers, captions, and image flag."""
        main_text, meta, usage = self._polish_draft(user_text, draft, usage)
        main_text = ensure_canonical_reply(main_text, user_text)
        main_text = ensure_belt_dealers_in_reply(main_text, user_text, history)
        # Only replace truncated buy/price answers — never force dealers elsewhere.
        if needs_polish(main_text) and (
            is_belt_price_query(user_text, history) or is_belt_supplier_query(user_text)
        ):
            main_text = ensure_belt_dealers_in_reply("", user_text, history)

        show_images = _resolve_show_reference_images(
            user_text, reference_images, meta, history, reply_text=main_text
        )
        if not show_images:
            main_text = strip_gallery_pointers(main_text)
        suggestions = meta.get("suggestions") or []
        if not suggestions:
            suggestions = local_suggestions(user_text, history)

        # Captions cost a model call and the gallery has a Bangla default line, so
        # only generate them when the farmer actually asked to be shown photos.
        caption_worthwhile = settings.ENABLE_IMAGE_CAPTIONS and (
            conversation_wants_visuals(user_text, history)
            or user_requests_visual_help(user_text)
        )
        captions: dict[int, str] = {}
        if show_images and reference_images and caption_worthwhile:
            try:
                cap_raw, cap_usage = self._generate_with_fallback(
                    [
                        self._types.Part.from_text(
                            text=caption_prompt(user_text, main_text, reference_images)
                        )
                    ],
                    config=self._caption_generation_config(get_knowledge_base()),
                    fast=True,
                )
                captions = parse_image_caption_lines(cap_raw)
                usage.input_tokens += cap_usage.input_tokens
                usage.output_tokens += cap_usage.output_tokens
                usage.cost_usd = round(usage.cost_usd + cap_usage.cost_usd, 6)
            except Exception:
                logger.exception("Caption generation failed.")

        return ChatReplyResult(
            text=main_text,
            image_captions=captions if show_images else {},
            suggestions=suggestions[:3],
            show_reference_images=show_images,
            usage=usage,
        )

    def _usage_from_response(self, response, model: str) -> UsageCost:
        inp, out = extract_usage(response)
        return UsageCost(
            input_tokens=inp,
            output_tokens=out,
            cost_usd=estimate_cost_usd(model, inp, out),
            model_used=model,
        )

    def _generate_with_fallback(
        self, contents: list, config=None, *, fast: bool = False
    ) -> tuple[str, UsageCost]:
        last_exc: Exception | None = None
        chain = settings.fast_model_chain if fast else settings.model_chain
        for model in chain:
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
        self._last_fast_path = None
        kb = get_knowledge_base()
        hit = try_fast_path(
            user_text, history, has_user_image=user_image_path is not None
        )
        if hit:
            self._last_fast_path = hit
            self._last_stream_buffer = hit.text
            self._last_stream_usage = UsageCost()
            yield hit.text
            return

        if not self.is_configured:
            yield _NO_KEY_MESSAGE
            return

        gemini_refs = self._catalog_images_for_gemini(reference_images, user_image_path)
        contents = self._build_chat_contents(
            history, user_text, gemini_refs, user_image_path
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
                if model != settings.GEMINI_MODEL:
                    logger.warning("Primary model failed; streamed with fallback %s.", model)
                self._last_stream_buffer = buffer
                self._last_stream_model = model
                self._last_stream_usage = usage
                return
            except Exception as exc:
                if _should_fallback(exc):
                    logger.warning(
                        "Model %s unavailable, trying next: %s", model, str(exc)[:160]
                    )
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
        """Polish streamed draft (Q+A review) into a complete final reply."""
        hit = getattr(self, "_last_fast_path", None)
        if isinstance(hit, FastPathHit):
            self._last_fast_path = None
            return self._result_from_fast_path(hit)

        raw = getattr(self, "_last_stream_buffer", "") or ""
        usage = getattr(self, "_last_stream_usage", None) or UsageCost(
            model_used=getattr(self, "_last_stream_model", settings.GEMINI_MODEL)
        )
        draft, _ = split_reply_metadata(raw)
        return self._assemble_chat_result(
            user_text, draft, reference_images, history, usage
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
            build_grounding_context(user_text, history, reference_images)
        )
        prompt_parts.append(
            "Reply in concise spoken Bangla. Answer THIS question only — "
            "do not paste a field recipe. Complete sentences. "
            "No ---META---, show_images, suggestions, or JSON in the visible text."
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
        hit = try_fast_path(
            user_text, history, has_user_image=user_image_path is not None
        )
        if hit:
            return self._result_from_fast_path(hit)

        kb = get_knowledge_base()
        if not self.is_configured:
            return ChatReplyResult(text=_NO_KEY_MESSAGE)

        gemini_refs = self._catalog_images_for_gemini(reference_images, user_image_path)
        contents = self._build_chat_contents(
            history, user_text, gemini_refs, user_image_path
        )

        try:
            raw, usage = self._stream_generate_with_fallback(
                contents, config=self._chat_generation_config(kb)
            )
            draft, _ = split_reply_metadata(raw)
            return self._assemble_chat_result(
                user_text, draft, reference_images, history, usage
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
                line = f"{role}: {content}"
                gallery = msg.get("gallery") or []
                if gallery:
                    labels = [
                        str(g.get("label") or g.get("image_name") or "").strip()
                        for g in gallery
                    ]
                    labels = [lab for lab in labels if lab]
                    if labels:
                        line += " [Photos shown: " + "; ".join(labels) + "]"
                lines.append(line)
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
