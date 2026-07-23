# Reference Images

Place photographs of the **intact / healthy** BRRI Winnower 2024 parts in this
folder. The backend automatically attaches these images to every Gemini Vision
request so the model can compare a user's (possibly broken) part against a
known-good reference.

## Guidelines

- Supported formats: `.jpg`, `.jpeg`, `.png`, `.webp`
- Use clear, well-lit, close-up photos of individual parts.
- Name files descriptively, e.g.:
  - `blower_unit_intact.jpg`
  - `v_belt_b65.jpg`
  - `pillow_block_p206.jpg`
  - `sieve_mechanism.jpg`
  - `main_shaft_bearing_6306.jpg`
- At most the first 4 images (alphabetical) are sent per request
  (`MAX_REFERENCE_IMAGES` in `app/routes/troubleshoot.py`).

> This `README.md` is ignored by the loader — only actual image files are used.
