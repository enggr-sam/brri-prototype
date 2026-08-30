import { renderReplyBlocks } from "../utils/formatReply.jsx";

/**
 * Farmer-facing Bangla. Turns **bold** / *italic* / ==highlight== into real markup
 * so stars never show in the chat.
 */
export default function MarkdownReply({ text, className = "" }) {
  if (!text) return null;

  return (
    <article
      className={`max-w-none font-bengali text-[15px] leading-relaxed ${className}`}
    >
      {renderReplyBlocks(text)}
    </article>
  );
}
