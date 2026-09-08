import { mediaUrl } from "../services/api.js";
import { formatReplyCostLabel } from "../utils/formatCost.js";
import MarkdownReply from "./MarkdownReply.jsx";

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
        className="inline-flex items-center gap-1.5 rounded-lg border border-leaf-500/20 bg-leaf-50 px-2.5 py-1.5 font-bengali text-xs font-medium text-leaf-800 transition hover:bg-blue-50"
      >
        ⬇️ নকশা ডাউনলোড
      </a>
    </div>
  );
}

function ReferenceGallery({ images }) {
  if (!images?.length) return null;

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <p className="mb-3 font-bengali text-sm font-medium text-slate-800">
        🖼️ ঠিক আছে এমন যন্ত্রাংশের ছবি — আপনার যন্ত্রাংশের সাথে তুলনা করুন
      </p>
      <div className="space-y-3">
        {images.map((img) => (
          <figure
            key={img.image_name}
            className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50"
          >
            <img
              src={mediaUrl(img.url)}
              alt={img.label}
              className="max-h-44 w-full bg-white object-contain sm:max-h-52"
              loading="lazy"
            />
            <figcaption className="px-3 py-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-bengali text-sm font-semibold text-slate-900">
                  {img.label}
                </p>
                {isCadDrawing(img) && (
                  <span className="rounded border border-leaf-500/20 bg-white px-1.5 py-0.5 font-bengali text-[10px] font-medium text-leaf-700">
                    CAD নকশা
                  </span>
                )}
              </div>
              {img.contextual_note ? (
                <p className="mt-1.5 font-bengali text-sm leading-relaxed text-slate-600">
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

function relativeTime(iso) {
  if (!iso) return "এইমাত্র";
  const delta = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(delta) || delta < 60_000) return "এইমাত্র";
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Dhaka",
  });
}

export default function ChatBubble({ message, showTimestamp = false }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex flex-col items-end">
        <div className="bubble-user max-w-[min(100%,20rem)] px-3.5 py-2.5 sm:max-w-[80%]">
          {showTimestamp && message.created_at && (
            <p className="mb-1 text-[11px] text-slate-400">
              {new Date(message.created_at).toLocaleString("bn-BD", {
                timeZone: "Asia/Dhaka",
                hour: "2-digit",
                minute: "2-digit",
                day: "numeric",
                month: "short",
              })}
            </p>
          )}
          <article className="whitespace-pre-wrap font-bengali text-[15px] leading-relaxed text-slate-800">
            {renderTextWithLinks(
              message.content,
              "break-all underline decoration-slate-400 underline-offset-2"
            )}
          </article>
          {message.attachment_url && (
            <div className="mt-2">
              {message.modality === "vision" ? (
                <img
                  src={mediaUrl(message.attachment_url)}
                  alt="Uploaded part"
                  className="max-h-48 w-full bg-white object-contain sm:max-h-52"
                />
              ) : (
                <p className="text-xs text-slate-500">🎙️ কণ্ঠ বার্তা</p>
              )}
            </div>
          )}
        </div>
        <p className="mt-1 pr-1 font-bengali text-[11px] text-slate-400">
          {relativeTime(message.created_at)}
        </p>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <img
        src="/brri-logo.jpg"
        alt=""
        className="mt-0.5 h-8 w-8 shrink-0 rounded-full bg-slate-100 object-contain p-0.5"
        aria-hidden
      />
      <div className="min-w-0 max-w-[min(100%,24rem)] flex-1 sm:max-w-[88%]">
        <p className="mb-1 text-xs font-semibold text-slate-600">BRRI সহায়ক</p>
        <MarkdownReply text={message.content} className="text-slate-800" />
        {message.reference_images?.length > 0 && (
          <ReferenceGallery images={message.reference_images} />
        )}
        {message.cost_usd > 0 && (
          <p className="mt-2 font-bengali text-[10px] text-slate-400">
            {formatReplyCostLabel(message.cost_usd)}
            {message.model_used ? ` · ${message.model_used}` : ""}
          </p>
        )}
      </div>
    </div>
  );
}
