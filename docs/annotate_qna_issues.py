#!/usr/bin/env python3
"""Stamp category + short reasoning onto the Winnower QnA issues PDF."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/home/enggr-sam-ft/Fahads_Tutorial/brri-prototype")
SRC_PAGES = Path("/tmp/winnower-qna")
OUT_PDF = ROOT / "Winnower QnA issues (27-08-26)-categorized.pdf"

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Categories:
# DOC      = data missing or wrong in the repo / collection form
# PROMPT   = wording, preferred Bangla name, × format, farmer terms — prompt only
# RETRIEVE = drawing/photo exists but the wrong one was shown
# CODE     = fast-path / app logic, not Gemini
# HALLUC   = invented a part or term that is not in the knowledge base

PAGE_NOTES: dict[int, list[str]] = {
    1: [
        "Q1  kg paddy per hour  ->  CODE + DOC. Fast-path treats any 'kg' as machine weight (97.86 kg). Even after that fix, kg/h capacity is not in the repo.",
        "Q2  2-acre cleaning time  ->  DOC. No throughput/time data in machine_data or collected specs. 'Not in documents' is honest until BRRI adds capacity.",
        "Q3  labour cost savings  ->  DOC. No labour-saving / economics figures anywhere in the knowledge base.",
    ],
    2: [
        "Q4  wheat/other crops  ->  PROMPT + DOC. Crop answer is fine. Preferred Bangla name (Bri Winnower / Bri dhan-gom jharai) is not in machine_data.json — add it, then tell the prompt to use it.",
        "Q5  how it works + hopper pic  ->  RETRIEVE. Hopper photos exist (field_04 / 02_hopper). Selector showed motor/belt instead of hopper.",
    ],
    3: [
        "Q6  pre-start checks  ->  PROMPT. Use sieve/chalni, not jal-er ongsho. Same part; farmer wording.",
        "Q7  main components  ->  PROMPT. Prefer chalni over 'oscillating jhorni' in farmer Bangla.",
        "Q8  frame material  ->  PROMPT. Write 38x38x3, never 38 gun 38 gun 3.",
    ],
    4: [
        "Q9  Fan diameter  ->  PROMPT + DOC. Same preferred Bangla name as Q4. Diameter 270 mm is in the repo.",
        "Q10 manufacturing cost  ->  DOC. Repo says Plain Carbon Steel; reviewer wants Mild Steel. Change machine_data / specs labels (MS is the shop name they want).",
        "Q11 dimension accuracy  ->  PROMPT. Name + x sign. Do not spell 'gun' for dimensions.",
    ],
    5: [
        "Q12 locally manufacture  ->  PROMPT + DOC. x format (prompt) and Mild Steel vs carbon steel (data label in repo).",
        "Q13 design modification  ->  HALLUC / PROMPT. 'Gusset plate' is not in the knowledge base — do not invent extra parts.",
    ],
    6: [
        "Q14 complete assembly drawing  ->  RETRIEVE. Sub-assembly 'Main body (BOM)' exploded sheets exist. App showed air-control field photos instead of those drawings.",
    ],
    7: [
        "Q15 exploded view + component names  ->  RETRIEVE (+ CAD image font). Exploded subasm sheets exist; CAD side-panel drawings were shown. Reviewer font??? is the CAD raster, not the chat UI.",
    ],
    8: [
        "Q16 shaft 2D + dimensions  ->  RETRIEVE + DOC. cad_26 sieve small shaft exists but was not shown; diameter/length are not in JSON. Name: prompt.",
        "Q17 Hopper CAD  ->  RETRIEVE. Hopper CAD sheets exist (cad_16/17). Show the hopper set, not one weak crop.",
        "Q18 component-wise BOM  ->  DOC. No BOM table file in the repo — only subasm sheets titled BOM. Collect/attach a real BOM as the note says.",
    ],
    9: [
        "Q19 how parts connect (CAD)  ->  RETRIEVE. Need exploded/assembly subasm, not a single hopper-bottom cutting drawing.",
        "Q20 engineering parameters  ->  PROMPT. chalona (driving) vs chalni (sieve) — model typo; specs already say sieve.",
    ],
    10: [
        "Q21 capacity 500 to 1000 kg/h  ->  CODE + DOC. Same fast-path kg->weight bug as Q1. No 500/1000 kg/h figure in the repo either.",
    ],
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_cover(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), (255, 252, 235))
    d = ImageDraw.Draw(img)
    title = font(28, True)
    h2 = font(18, True)
    body = font(15)
    small = font(13)
    y = 48
    d.text((48, y), "Winnower QnA issues (27-08-26) — categories", font=title, fill=(40, 40, 20))
    y = 96
    d.text((48, y), "Source: reviewer PDF. Notes added under each question.", font=small, fill=(80, 80, 60))
    y = 140
    legend = [
        ("DOC", "Documentation / data", "Fact is missing or wrong in the repo (machine_data, specs, no BOM, no kg/h, name, mild steel). Adding a prompt cannot invent a number that is not there."),
        ("PROMPT", "Prompt / wording only", "Same facts; change how it is said: preferred Bangla local name, chalni/sieve not jal/jhorni, 38x38x3 not the word gun, chalni not chalona."),
        ("RETRIEVE", "Wrong photo/drawing shown", "The file is already in collected/photos or CAD/subasm, but the selector showed a different part."),
        ("CODE", "App logic (not Gemini)", "Local fast-path: any question with কেজি/kg is answered as machine weight 97.86 kg."),
        ("HALLUC", "Invented, not in KB", "Named a part the evidence does not list (e.g. gusset plate). Prompt: never invent parts."),
    ]
    d.text((48, y), "Category legend", font=h2, fill=(40, 40, 20))
    y += 36
    for code, name, blurb in legend:
        d.rectangle((48, y, 140, y + 26), fill=(255, 230, 80), outline=(120, 90, 0))
        d.text((56, y + 4), code, font=font(13, True), fill=(40, 40, 10))
        d.text((152, y + 4), name, font=font(15, True), fill=(40, 40, 20))
        y += 30
        for line in wrap(d, blurb, body, w - 96):
            d.text((56, y), line, font=body, fill=(50, 50, 40))
            y += 22
        y += 10

    y += 8
    d.text((48, y), "Counts (21 questions; some have two tags)", font=h2, fill=(40, 40, 20))
    y += 32
    counts = [
        "DOC: Q2, Q3, Q4/Q9 (name in data), Q10/Q12 (mild steel), Q16 (shaft dims), Q18 (BOM file), Q1/Q21 (no kg/h after code fix)",
        "PROMPT: Q4/Q9/Q11 name, Q6/Q7 sieve=chalni, Q8/Q11/Q12 x sign, Q20 chalni vs chalona",
        "RETRIEVE: Q5 hopper photo, Q14 assembly, Q15 exploded, Q16 shaft CAD, Q17 hopper CAD, Q19 connections",
        "CODE: Q1, Q21 (fast-path weight)",
        "HALLUC: Q13 gusset plate",
    ]
    for line in counts:
        for wrapped in wrap(d, line, body, w - 96):
            d.text((56, y), wrapped, font=body, fill=(40, 40, 30))
            y += 22
        y += 8
    return img


def annotate_page(page_no: int) -> Image.Image:
    src = Image.open(SRC_PAGES / f"page-{page_no:02d}.png").convert("RGB")
    notes = PAGE_NOTES[page_no]
    fnt = font(15)
    dummy = ImageDraw.Draw(src)
    max_w = src.width - 72
    wrapped: list[str] = []
    for note in notes:
        wrapped.extend(wrap(dummy, note, fnt, max_w))
        wrapped.append("")
    while wrapped and wrapped[-1] == "":
        wrapped.pop()
    line_h = 22
    pad = 28
    header_h = 36
    extra = header_h + pad * 2 + line_h * len(wrapped)
    out = Image.new("RGB", (src.width, src.height + extra), (255, 249, 196))
    out.paste(src, (0, 0))
    d = ImageDraw.Draw(out)
    y0 = src.height
    d.line((0, y0, src.width, y0), fill=(180, 140, 0), width=3)
    d.text((36, y0 + 10), f"Category note — page {page_no}", font=font(16, True), fill=(80, 50, 0))
    y = y0 + header_h
    for line in wrapped:
        if line:
            d.text((36, y), line, font=fnt, fill=(40, 30, 10))
        y += line_h
    return out


def main() -> None:
    pages = [make_cover(1241, 1754)]
    for n in range(1, 11):
        pages.append(annotate_page(n))
    pages[0].save(
        OUT_PDF,
        save_all=True,
        append_images=pages[1:],
        resolution=150.0,
    )
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
