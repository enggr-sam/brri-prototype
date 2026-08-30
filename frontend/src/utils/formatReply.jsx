import { Fragment } from "react";

function normalize(text) {
  return String(text ?? "")
    .replace(/[\u200B\u200C\u200D\uFEFF]/g, "")
    .replace(/\uFF0A/g, "*")
    .replace(/\\([*_])/g, "$1")
    .replace(/\*{1,2}\s*$/, "");
}

/**
 * Gemini often writes ** bold ** with spaces. CommonMark leaves those as stars.
 */
const INLINE_RE =
  /\*\*\s*([^*]+?)\s*\*\*|__\s*([^_]+?)\s*__|==\s*([^=]+?)\s*==|\*(?!\*)\s*([^\n*]*[\p{L}][^\n*]*)\s*\*(?!\*)/gu;

function renderInline(text, keyPrefix) {
  const nodes = [];
  let last = 0;
  let i = 0;
  const re = new RegExp(INLINE_RE.source, INLINE_RE.flags);
  let match = re.exec(text);
  while (match) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const bold = match[1] ?? match[2];
    const highlight = match[3];
    const italic = match[4];
    if (bold != null) {
      nodes.push(
        <strong
          key={`${keyPrefix}-b${i}`}
          className="rounded-sm bg-amber-100 px-0.5 font-bengali font-bold text-leaf-950"
        >
          {bold}
        </strong>
      );
    } else if (highlight != null) {
      nodes.push(
        <mark
          key={`${keyPrefix}-h${i}`}
          className="rounded-sm bg-amber-100 px-0.5 font-bengali font-semibold text-leaf-950"
        >
          {highlight}
        </mark>
      );
    } else if (italic != null) {
      nodes.push(
        <em key={`${keyPrefix}-i${i}`} className="font-bengali italic">
          {italic}
        </em>
      );
    }
    last = match.index + match[0].length;
    i += 1;
    match = re.exec(text);
  }
  if (last < text.length) {
    nodes.push(text.slice(last));
  }
  return nodes;
}

function isBullet(line) {
  return /^\s*(?:[-•]|\d+[.)])\s+/.test(line);
}

function stripBullet(line) {
  return line.replace(/^\s*(?:[-•]|\d+[.)])\s+/, "");
}

export function renderReplyBlocks(raw) {
  const text = normalize(raw).replace(/\r\n/g, "\n").trim();
  if (!text) return null;

  const lines = text.split("\n");
  const blocks = [];
  let i = 0;
  let b = 0;

  while (i < lines.length) {
    if (!lines[i].trim()) {
      i += 1;
      continue;
    }
    if (isBullet(lines[i])) {
      const items = [];
      while (i < lines.length && isBullet(lines[i])) {
        items.push(stripBullet(lines[i]));
        i += 1;
      }
      blocks.push(
        <ul key={`ul-${b}`} className="mb-2 list-disc pl-5 last:mb-0">
          {items.map((item, idx) => (
            <li key={`li-${b}-${idx}`} className="mb-0.5">
              {renderInline(item, `l${b}-${idx}`)}
            </li>
          ))}
        </ul>
      );
      b += 1;
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !isBullet(lines[i])) {
      para.push(lines[i]);
      i += 1;
    }
    blocks.push(
      <p key={`p-${b}`} className="mb-2 last:mb-0">
        {para.map((line, idx) => (
          <Fragment key={`ln-${b}-${idx}`}>
            {idx > 0 ? <br /> : null}
            {renderInline(line, `p${b}-${idx}`)}
          </Fragment>
        ))}
      </p>
    );
    b += 1;
  }

  return blocks;
}
