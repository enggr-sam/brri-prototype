import { mediaUrl } from "../services/api.js";
import { formatReplyCostLabel } from "../utils/formatCost.js";

const URL_PATTERN = /(https?:\/\/[^\s]+)/g;

function isCadDrawing(img) {
  const source = (img.source || "").toLowerCase();
  const name = (img.image_name || "").toLowerCase();
  return source === "cad_drawing" || name.startsWith("cad_");
}

function isDriveUrl(url) {
  return typeof url === "string" && /drive\.google\.com|docs\.google\.com/i.test(url);
}

function renderTextWithLinks(text, linkClass) {
  if (!text) return null;
  const parts = text.split(URL_PATTERN);
  return parts.map((part, index) => {
    if (!part.startsWith("http")) return part;
    // Drive links are never shown — images live in the in-app gallery.
    if (isDriveUrl(part)) return null;
    return (
      <a
        key={`link-${index}`}
        href={part}
        target="_blank"
        rel="noopener noreferrer"
        className={linkClass}
      >
        {part}
      </a>
    );
  });
}

function GalleryActions({ img }) {
  const href = mediaUrl(img.url);
  if (!isCadDrawing(img) || !href) return null;

  return (
    <div className="mt-2.5 flex flex-wrap gap-2">
      <a
        href={`${href}${href.includes("?") ? "&" : "?"}download=1`}
        download={img.image_name || "cad-drawing.jpg"}
        className="inline-flex items-center gap-1.5 border border-leaf-500/25 bg-leaf-50 px-2.5 py-1.5 font-bengali text-xs font-medium text-leaf-900 transition hover:bg-leaf-100"
      >
        ⬇️ নকশা ডাউনলোড
      </a>
    </div>
  );
}

function ReferenceGallery({ images }) {
  if (!images?.length) return null;

  return (
    <div className="mt-4 border-t border-leaf-900/10 pt-4">
      <p className="mb-3 font-bengali text-sm font-medium text-leaf-950">
        🖼️ ঠিক আছে এমন যন্ত্রাংশের ছবি — আপনার যন্ত্রাংশের সাথে তুলনা করুন
      </p>
      <div className="space-y-3">
        {images.map((img) => (
          <figure
            key={img.image_name}
            className="overflow-hidden border border-leaf-900/10 bg-leaf-50/60"
          >
            <img
              src={mediaUrl(img.url)}
              alt={img.label}
              className="max-h-44 w-full bg-white object-contain sm:max-h-52"
              loading="lazy"
            />
            <figcaption className="px-3 py-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-bengali text-sm font-semibold text-leaf-950">
                  {img.label}
                </p>
                {isCadDrawing(img) && (
                  <span className="border border-leaf-500/20 bg-white px-1.5 py-0.5 font-bengali text-[10px] font-medium text-leaf-800">
                    CAD নকশা
                  </span>
                )}
              </div>
              {img.contextual_note ? (
                <p className="mt-1.5 font-bengali text-sm leading-relaxed text-leaf-900/80">
                  {img.contextual_note}
                </p>
              ) : null}
              <GalleryActions img={img} />
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}

export default function ChatBubble({ message, showTimestamp = false }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[min(100%,24rem)] px-3.5 py-3 sm:max-w-[88%] sm:px-4 ${
          isUser
            ? "rounded-2xl rounded-br-md bg-leaf-500 text-white"
            : "rounded-2xl rounded-bl-md bg-white shadow-sm ring-1 ring-leaf-900/8"
        }`}
      >
        {showTimestamp && message.created_at && (
          <p
            className={`mb-2 text-[11px] ${
              isUser ? "text-white/70" : "text-leaf-800/50"
            }`}
          >
            {new Date(message.created_at).toLocaleString("bn-BD", {
              timeZone: "Asia/Dhaka",
              hour: "2-digit",
              minute: "2-digit",
              day: "numeric",
              month: "short",
            })}
          </p>
        )}
        {!isUser && (
          <div className="mb-2 flex items-center gap-2">
            <img
              src="/brri-logo.jpg"
              alt=""
              className="h-5 w-5 object-contain"
              aria-hidden
            />
            <p className="text-xs font-medium text-leaf-500">BRRI সহায়ক</p>
          </div>
        )}

        <article
          className={`max-w-none whitespace-pre-wrap font-bengali text-[15px] leading-relaxed ${
            isUser ? "text-white" : "text-leaf-950"
          }`}
        >
          {renderTextWithLinks(
            message.content,
            isUser
              ? "break-all underline decoration-white/60 underline-offset-2"
              : "break-all text-leaf-500 underline decoration-leaf-500/40 underline-offset-2"
          )}
        </article>

        {message.attachment_url && isUser && (
          <div className="mt-3">
            {message.modality === "vision" ? (
              <img
                src={mediaUrl(message.attachment_url)}
                alt="Uploaded part"
                className="max-h-48 w-full bg-black/10 object-contain sm:max-h-52"
              />
            ) : (
              <p className="text-xs opacity-90">🎙️ কণ্ঠ বার্তা</p>
            )}
          </div>
        )}

        {!isUser && message.reference_images?.length > 0 && (
          <ReferenceGallery images={message.reference_images} />
        )}

        {!isUser && message.cost_usd > 0 && (
          <p className="mt-2 border-t border-leaf-900/10 pt-2 font-bengali text-[10px] text-leaf-800/45">
            {formatReplyCostLabel(message.cost_usd)}
            {message.model_used ? ` · ${message.model_used}` : ""}
          </p>
        )}
      </div>
    </div>
  );
}
