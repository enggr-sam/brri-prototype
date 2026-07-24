# Reference Images

Place photographs of the **intact / healthy** BRRI Winnower 2024 parts in this
folder. The backend automatically attaches these images to every Gemini Vision
request so the model can compare a user's (possibly broken) part against a
known-good reference.

## Guidelines

- Supported formats: `.jpg`, `.jpeg`, `.png`, `.webp`
- Use clear, well-lit, close-up photos of individual parts.
- Files are named `NN_descriptive_name.jpg` (a two-digit number prefix keeps them
  ordered and ties them to the catalogue), e.g.:
  - `01_brri_winnower_motor_pulley_and_belt_system.jpg`
  - `27_v_belt_b65_marking_closeup.jpg`
  - `30_sieve_drive_arm_and_pillow_bearing_side_view.jpg`
- At most **8** relevant images are attached per request (smart selection based
  on the user's text; configurable via `MAX_REFERENCE_IMAGES` in `.env`).

## Descriptions catalogue

Each image has a numbered entry (with a description + troubleshooting context) in
[`../reference_images.json`](../reference_images.json). At startup the backend
loads this catalogue and:

- injects **all** image descriptions into Gemini's system instruction (cheap
  text, so the model knows every intact part exists), and
- attaches each actual reference image alongside its specific description.

To add a new reference image: drop the file here as `NN_name.jpg` and add a
matching entry to `reference_images.json`. Changes are picked up automatically
on the next API request (or call `POST /api/knowledge-base/reload`).

> This `README.md` is ignored by the loader — only actual image files are used.
