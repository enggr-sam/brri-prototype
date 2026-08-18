"""Unicode normalisation for Bangla input.

Bangla letters that carry a nukta have two valid encodings: precomposed (য় = U+09DF)
and decomposed (য + ় = U+09AF U+09BC). Different Android keyboards, iOS, and the
model itself emit different forms, and the two never compare equal as raw strings — so
a keyword list containing "কোথায়" silently fails to match a farmer who typed the other
form. Folding everything to NFC on the way in makes one spelling enough.
"""

from __future__ import annotations

import unicodedata


def nfc(text: str) -> str:
    """Normalise to NFC so nukta variants compare equal."""
    if not text:
        return text
    return unicodedata.normalize("NFC", text)
