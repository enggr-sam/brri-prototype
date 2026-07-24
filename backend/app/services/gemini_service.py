"""Google Gemini 2.5 Pro integration.

Wraps the multimodal ``google-genai`` SDK. The service is responsible for:

* Building the grounded system instruction from the knowledge base.
* Attaching local "healthy part" reference images so the model can compare the
  user's (potentially broken) part against a known-good reference.
* Analysing an uploaded image + optional text (vision flow).
* Transcribing an uploaded audio clip and producing a troubleshooting answer
  (voice flow).

If ``GEMINI_API_KEY`` is not configured the service degrades gracefully and
returns an explanatory Bengali message instead of crashing, so the prototype
remains runnable for UI demos without a key.
"""

import logging
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.knowledge_base import KnowledgeBase, get_knowledge_base
from app.utils.image_captions import caption_prompt, parse_image_caption_lines

logger = logging.getLogger(__name__)

# Bengali message shown when the API key is missing (keeps the app demoable).
_NO_KEY_MESSAGE = (
    "দুঃখিত, এই মুহূর্তে AI সহায়তা সেবাটি কনফিগার করা হয়নি। "
    "অনুগ্রহ করে সার্ভারের `.env` ফাইলে একটি বৈধ `GEMINI_API_KEY` যুক্ত করুন। "
    "(Server is missing a valid GEMINI_API_KEY.)"
)


class QuotaExceededError(Exception):
    """Raised when every model in the chain returns a 429 (quota exhausted)."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class ChatReplyResult:
    text: str
    image_captions: dict[int, str] = field(default_factory=dict)


def _is_quota_error(exc: Exception) -> bool:
    """Detect a Gemini 429 / RESOURCE_EXHAUSTED error across SDK versions."""
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status == 429:
        return True
    text = str(exc).upper()
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def _should_fallback(exc: Exception) -> bool:
    """Whether to try the next model: quota (429), model unavailable/retired
    (404 NOT_FOUND), or temporary overload (503 UNAVAILABLE)."""
    if _is_quota_error(exc):
        return True
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status in (404, 503):
        return True
    text = str(exc).upper()
    return "NOT_FOUND" in text or "UNAVAILABLE" in text


# Gemini-supported audio MIME types keyed by file extension. This is used
# instead of ``mimetypes.guess_type`` because the stdlib maps ``.webm`` to
# ``video/webm`` — which makes Gemini try to decode it as video ("0 Frames
# found"). Browser MediaRecorder produces webm/opus or ogg audio.
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
    """Return a valid ``audio/*`` MIME type for an audio file.

    Prefers the caller-provided content type (from the browser upload) when it
    is already an audio type, otherwise maps the file extension explicitly.
    Never returns a ``video/*`` type.
    """
    if provided:
        # Strip any codec parameter, e.g. "audio/webm;codecs=opus".
        base = provided.split(";")[0].strip().lower()
        if base.startswith("audio/"):
            return base
    return _AUDIO_EXT_MIME.get(path.suffix.lower(), "audio/webm")


def _retry_after_seconds(exc: Exception | None) -> int | None:
    """Best-effort parse of the 'Please retry in 54.3s' hint from the error."""
    if exc is None:
        return None
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc))
    if match:
        return int(float(match.group(1))) + 1
    return None


class GeminiService:
    """Thin, testable wrapper around the Gemini multimodal client."""

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
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Failed to initialise Gemini client: %s", exc)
        else:
            logger.warning("GEMINI_API_KEY not set; running in offline/demo mode.")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    # -- Internal helpers -------------------------------------------------

    def _image_part(self, path: Path):
        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "image/jpeg"
        return self._types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)

    def _reference_image_parts(self, reference_images: list[Path]) -> list:
        """Attach reference images with a SHORT label (full catalogue is already
        in the system instruction — long per-image text makes replies verbose)."""
        kb = get_knowledge_base()
        parts: list = []
        for img in reference_images:
            entry = kb._by_name.get(img.name, {})
            num = entry.get("image_number")
            desc = entry.get("description") or ""
            # Keep only the troubleshooting hook, not the full paragraph.
            if "Troubleshooting context:" in desc:
                short = desc.split("Troubleshooting context:", 1)[-1].strip()
            else:
                short = desc[:120].strip()
            label = f"[Reference #{num}: {img.name}]"
            if short:
                label += f"\n{short[:180]}"
            parts.append(self._types.Part.from_text(text=label))
            parts.append(self._image_part(img))
        return parts

    def _chat_generation_config(self, kb: KnowledgeBase):
        """Generation settings for clear, complete chat replies."""
        return self._types.GenerateContentConfig(
            system_instruction=kb.build_system_instruction(),
            max_output_tokens=2048,
            temperature=0.5,
        )

    def _generate(self, contents: list, kb: KnowledgeBase, *, chat: bool = False) -> str:
        config = (
            self._chat_generation_config(kb)
            if chat
            else self._types.GenerateContentConfig(
                system_instruction=kb.build_system_instruction(),
            )
        )
        return self._generate_with_fallback(contents, config=config)

    def _generate_with_fallback(self, contents: list, config=None) -> str:
        """Run ``generate_content`` across the model chain.

        Tries the primary model first; on a 429 quota error it transparently
        falls back to the next model (e.g. gemini-2.5-flash). If every model is
        exhausted, raises ``QuotaExceededError``.
        """
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
                    parts = getattr(response, "candidates", None) or []
                    if parts:
                        content = getattr(parts[0], "content", None)
                        if content and getattr(content, "parts", None):
                            text = "".join(
                                getattr(p, "text", "") or "" for p in content.parts
                            ).strip()
                finish = None
                if getattr(response, "candidates", None):
                    finish = getattr(response.candidates[0], "finish_reason", None)
                if finish and str(finish).endswith("MAX_TOKENS"):
                    logger.warning(
                        "Gemini reply truncated (finish_reason=%s, len=%d).",
                        finish,
                        len(text),
                    )
                if model != settings.GEMINI_MODEL:
                    logger.warning("Primary model failed; used fallback %s.", model)
                return text
            except Exception as exc:  # noqa: BLE001 - inspect then decide
                if _should_fallback(exc):
                    logger.warning("Model %s unavailable, trying next: %s", model, str(exc)[:120])
                    last_exc = exc
                    continue
                raise

        raise QuotaExceededError(
            "All configured Gemini models are unavailable or quota-exhausted.",
            retry_after=_retry_after_seconds(last_exc),
        )

    def _caption_generation_config(self, kb: KnowledgeBase):
        return self._types.GenerateContentConfig(
            system_instruction=kb.build_system_instruction(),
            max_output_tokens=1024,
            temperature=0.4,
        )

    def _generate_image_captions(
        self,
        user_text: str,
        reply: str,
        reference_images: list[Path],
        kb: KnowledgeBase,
    ) -> dict[int, str]:
        if not reference_images:
            return {}

        prompt = caption_prompt(user_text, reply, reference_images)
        raw = self._generate_with_fallback(
            [self._types.Part.from_text(text=prompt)],
            config=self._caption_generation_config(kb),
        )
        return parse_image_caption_lines(raw)

    def chat_reply(
        self,
        history: list[dict[str, str]],
        user_text: str,
        reference_images: list[Path],
        user_image_path: Path | None = None,
    ) -> ChatReplyResult:
        """Multi-turn chat: history + optional new image + reference grounding."""
        from app.utils.response_filter import filter_assistant_reply

        kb = get_knowledge_base()
        if not self.is_configured:
            return ChatReplyResult(text=_NO_KEY_MESSAGE)

        types = self._types
        contents: list = []
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
            "Write complete sentences in natural spoken Bangla. "
            "Include a full 'সমাধান:' section with 2–3 detailed steps (not half sentences). "
            "No markdown. Plain text only. If images help, say to compare with photos below."
        )
        contents.append(types.Part.from_text(text="\n\n".join(prompt_parts)))

        try:
            raw = self._generate(contents, kb, chat=True)
            main_text = filter_assistant_reply(raw)
            captions = (
                self._generate_image_captions(
                    user_text, main_text, reference_images, kb
                )
                if reference_images
                else {}
            )
            return ChatReplyResult(text=main_text, image_captions=captions)
        except Exception as exc:
            logger.exception("Chat request failed: %s", exc)
            raise

    @staticmethod
    def _format_history(history: list[dict[str, str]], limit: int = 6) -> str:
        """Serialise recent turns — truncated so the model does not re-copy long replies."""
        lines: list[str] = []
        for msg in history[-limit:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = (msg.get("content") or "").strip()
            if len(content) > 280:
                content = content[:280].rstrip() + "…"
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    # -- Public API -------------------------------------------------------

    def analyze_image(
        self,
        image_path: Path,
        user_text: str | None,
        reference_images: list[Path],
    ) -> str:
        """Vision flow: analyse a user's part photo against reference images."""
        kb = get_knowledge_base()
        if not self.is_configured:
            return _NO_KEY_MESSAGE

        types = self._types
        contents: list = []
        contents.extend(self._reference_image_parts(reference_images))
        contents.append(
            types.Part.from_text(
                text="[User uploaded image of the part that may be faulty:]"
            )
        )
        contents.append(self._image_part(image_path))

        user_prompt = (
            user_text.strip()
            if user_text and user_text.strip()
            else "এই যন্ত্রাংশে কী সমস্যা হতে পারে তা বিশ্লেষণ করুন।"
        )
        contents.append(types.Part.from_text(text=f"User note: {user_prompt}"))

        try:
            return self._generate(contents, kb)
        except Exception as exc:  # pragma: no cover - network/runtime errors
            logger.exception("Gemini vision request failed: %s", exc)
            raise

    def transcribe_audio(self, audio_path: Path, content_type: str | None = None) -> str:
        """Transcribe an audio clip to text (kept as a separate step so the
        transcription can be stored and displayed independently)."""
        if not self.is_configured:
            return ""

        types = self._types
        mime = _resolve_audio_mime(audio_path, content_type)
        audio_part = types.Part.from_bytes(data=audio_path.read_bytes(), mime_type=mime)
        prompt = types.Part.from_text(
            text=(
                "Transcribe the following audio verbatim. The speaker is most "
                "likely describing a problem with an agricultural winnower "
                "machine, possibly in Bengali. Return ONLY the transcription text."
            )
        )
        return self._generate_with_fallback([prompt, audio_part])

    def analyze_voice(
        self,
        audio_path: Path,
        transcription: str,
        reference_images: list[Path],
    ) -> str:
        """Voice flow: produce a troubleshooting answer from the transcription.

        Reference images are still attached so the model retains visual context
        of the intact machine parts while reasoning about the described issue.
        """
        kb = get_knowledge_base()
        if not self.is_configured:
            return _NO_KEY_MESSAGE

        types = self._types
        contents: list = []
        contents.extend(self._reference_image_parts(reference_images))
        described = transcription.strip() or "(transcription unavailable)"
        contents.append(
            types.Part.from_text(
                text=(
                    "The user described the following issue with the BRRI "
                    f"Winnower 2024 (transcribed from voice):\n\n\"{described}\"\n\n"
                    "Provide a step-by-step troubleshooting solution."
                )
            )
        )

        try:
            return self._generate(contents, kb)
        except Exception as exc:  # pragma: no cover
            logger.exception("Gemini voice request failed: %s", exc)
            raise


# Module-level singleton reused across requests.
gemini_service = GeminiService()
