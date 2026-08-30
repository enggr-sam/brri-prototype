import ReactMarkdown from "react-markdown";

function isDriveUrl(url) {
  return typeof url === "string" && /drive\.google\.com|docs\.google\.com/i.test(url);
}

/**
 * Farmer-facing Bangla with **bold** / *italic* from the assistant.
 */
export default function MarkdownReply({ text, className = "" }) {
  if (!text) return null;

  return (
    <article className={`max-w-none font-bengali text-[15px] leading-relaxed ${className}`}>
      <ReactMarkdown
        urlTransform={(url) => (isDriveUrl(url) ? "" : url)}
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          strong: ({ children }) => (
            <strong className="font-semibold">{children}</strong>
          ),
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => (
            <ul className="mb-2 list-disc pl-5 last:mb-0">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2 list-decimal pl-5 last:mb-0">{children}</ol>
          ),
          li: ({ children }) => <li className="mb-0.5">{children}</li>,
          h1: ({ children }) => (
            <p className="mb-2 font-semibold">{children}</p>
          ),
          h2: ({ children }) => (
            <p className="mb-2 font-semibold">{children}</p>
          ),
          h3: ({ children }) => (
            <p className="mb-2 font-semibold">{children}</p>
          ),
          a: ({ href, children }) =>
            href && !isDriveUrl(href) ? (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="break-all text-leaf-500 underline decoration-leaf-500/40 underline-offset-2"
              >
                {children}
              </a>
            ) : (
              children
            ),
        }}
      >
        {text}
      </ReactMarkdown>
    </article>
  );
}
