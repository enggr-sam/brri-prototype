import { mediaUrl } from "../services/api.js";
import { formatReplyCostLabel } from "../utils/formatCost.js";

function ReferenceGallery({ images }) {
  if (!images?.length) return null;

  return (
    <div className="mt-4 border-t border-slate-100 pt-4">
      <p className="mb-3 text-sm font-medium text-brri-dark">
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
              className="max-h-48 w-full object-contain bg-white"
              loading="lazy"
            />
            <figcaption className="px-3 py-2.5">
              <p className="text-sm font-semibold text-brri-dark">
                #{img.image_number} {img.label}
              </p>
              {img.contextual_note ? (
                <p className="mt-1.5 font-bengali text-sm leading-relaxed text-slate-700">
                  {img.contextual_note}
                </p>
              ) : img.description ? (
                <p className="mt-1.5 font-bengali text-sm leading-relaxed text-slate-600">
                  এই ছবিতে ঠিক অংশ দেখানো হয়েছে — আপনার যন্ত্রাংশের সাথে মিলিয়ে দেখুন।
                </p>
              ) : null}
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
        className={`max-w-[92%] rounded-2xl px-4 py-3 sm:max-w-[88%] ${
          isUser
            ? "rounded-br-md bg-brri-green text-white"
            : "rounded-bl-md bg-white shadow-sm ring-1 ring-slate-100"
        }`}
      >
        {showTimestamp && message.created_at && (
          <p
            className={`mb-2 text-[11px] ${
              isUser ? "text-white/70" : "text-slate-400"
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
            <p className="text-xs font-medium text-brri-green">BRRI সহায়ক</p>
          </div>
        )}

        {/* Text first — then images (easier to read) */}
        <article
          className={`max-w-none whitespace-pre-wrap font-bengali text-[15px] leading-relaxed ${
            isUser ? "text-white" : "text-slate-800"
          }`}
        >
          {message.content}
        </article>

        {message.attachment_url && isUser && (
          <div className="mt-3">
            {message.modality === "vision" ? (
              <img
                src={mediaUrl(message.attachment_url)}
                alt="Uploaded part"
                className="max-h-52 w-full rounded-lg object-contain bg-black/10"
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
          <p className="mt-2 border-t border-slate-100 pt-2 font-bengali text-[10px] text-slate-400">
            {formatReplyCostLabel(message.cost_usd)}
            {message.model_used ? ` · ${message.model_used}` : ""}
          </p>
        )}
      </div>
    </div>
  );
}
