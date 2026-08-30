import MarkdownReply from "./MarkdownReply.jsx";

/**
 * Renders the Bengali troubleshooting answer returned by the backend.
 */
export default function ResponseDisplay({ result }) {
  if (!result) return null;

  return (
    <div className="rounded-xl border border-brri-light bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-brri-dark">
          <span>✅</span> সমাধান (Solution)
        </h2>
        <span className="rounded-full bg-brri-light px-2.5 py-0.5 text-xs font-medium text-brri-dark">
          {result.modality === "voice" ? "🎙️ Voice" : "📷 Vision"}
        </span>
      </div>

      {result.transcription && (
        <div className="mb-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
          <span className="font-semibold">Transcription:</span>{" "}
          {result.transcription}
        </div>
      )}

      <MarkdownReply text={result.response} className="text-slate-800" />

      {result.reference_images_used?.length > 0 && (
        <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">
          তুলনা করা হয়েছে: {result.reference_images_used.join(", ")}
        </p>
      )}
    </div>
  );
}
