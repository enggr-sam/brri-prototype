import { mediaUrl } from "../services/api.js";

function ReferenceGallery({ images }) {
  if (!images?.length) return null;

  return (
    <div className="mt-3 border-t border-slate-100 pt-3">
      <p className="mb-2 text-xs font-medium text-slate-500">
        🖼️ তুলনা করা হয়েছে:
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {images.map((img) => (
          <figure
            key={img.image_name}
            className="overflow-hidden rounded-lg border border-slate-200 bg-white"
          >
            <img
              src={mediaUrl(img.url)}
              alt={img.label}
              className="h-24 w-full object-cover"
              loading="lazy"
            />
            <figcaption className="px-2 py-1.5">
              <p className="truncate text-xs font-medium text-brri-dark">
                #{img.image_number} {img.label}
              </p>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}

export default function ChatBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[92%] rounded-2xl px-4 py-3 sm:max-w-[85%] ${
          isUser
            ? "rounded-br-md bg-brri-green text-white"
            : "rounded-bl-md bg-white shadow-sm ring-1 ring-slate-100"
        }`}
      >
        {!isUser && (
          <p className="mb-1 text-xs font-medium text-brri-green">🌾 BRRI সহায়ক</p>
        )}

        {message.attachment_url && isUser && (
          <div className="mb-2">
            {message.modality === "vision" ? (
              <img
                src={mediaUrl(message.attachment_url)}
                alt="Uploaded"
                className="max-h-40 rounded-lg object-cover"
              />
            ) : (
              <p className="text-xs opacity-90">🎙️ Voice message</p>
            )}
          </div>
        )}

        <article
          className={`max-w-none whitespace-pre-wrap font-bengali text-[15px] leading-relaxed ${
            isUser ? "text-white" : "text-slate-800"
          }`}
        >
          {message.content}
        </article>

        {!isUser && <ReferenceGallery images={message.reference_images} />}
      </div>
    </div>
  );
}
