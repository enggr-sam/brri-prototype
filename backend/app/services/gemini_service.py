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
from pathlib import Path

from app.config import settings
from app.services.knowledge_base import KnowledgeBase, get_knowledge_base

logger = logging.getLogger(__name__)

# Bengali message shown when the API key is missing (keeps the app demoable).
_NO_KEY_MESSAGE = (
    "দুঃখিত, এই মুহূর্তে AI সহায়তা সেবাটি কনফিগার করা হয়নি। "
    "অনুগ্রহ করে সার্ভারের `.env` ফাইলে একটি বৈধ `GEMINI_API_KEY` যুক্ত করুন। "
    "(Server is missing a valid GEMINI_API_KEY.)"
)


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
        """Wrap each reference image with a small label so the model knows the
        images are the *intact* parts to compare against."""
        parts: list = []
        for img in reference_images:
            parts.append(
                self._types.Part.from_text(
                    text=f"[Reference image of an INTACT machine part: {img.name}]"
                )
            )
            parts.append(self._image_part(img))
        return parts

    def _generate(self, contents: list, kb: KnowledgeBase) -> str:
        config = self._types.GenerateContentConfig(
            system_instruction=kb.build_system_instruction(),
        )
        response = self._client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        return (response.text or "").strip()

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

    def transcribe_audio(self, audio_path: Path) -> str:
        """Transcribe an audio clip to text (kept as a separate step so the
        transcription can be stored and displayed independently)."""
        if not self.is_configured:
            return ""

        types = self._types
        mime, _ = mimetypes.guess_type(str(audio_path))
        mime = mime or "audio/webm"
        audio_part = types.Part.from_bytes(data=audio_path.read_bytes(), mime_type=mime)
        prompt = types.Part.from_text(
            text=(
                "Transcribe the following audio verbatim. The speaker is most "
                "likely describing a problem with an agricultural winnower "
                "machine, possibly in Bengali. Return ONLY the transcription text."
            )
        )
        response = self._client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[prompt, audio_part],
        )
        return (response.text or "").strip()

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
