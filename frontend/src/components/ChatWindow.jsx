import { useEffect, useRef } from "react";
import ChatBubble from "./ChatBubble.jsx";
import FollowUpSuggestions from "./FollowUpSuggestions.jsx";
import Loader from "./Loader.jsx";

export default function ChatWindow({
  messages,
  streamingText,
  loading,
  error,
  suggestions,
  onSuggestionClick,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, loading]);

  return (
    <div
      className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-y-contain px-4 py-4"
      style={{ WebkitOverflowScrolling: "touch" }}
    >
      {messages.map((msg) => (
        <ChatBubble key={msg.id ?? `${msg.role}-${msg.created_at}`} message={msg} />
      ))}

      {streamingText && (
        <div className="flex justify-start">
          <div className="max-w-[92%] rounded-2xl rounded-bl-md bg-white px-4 py-3 shadow-sm ring-1 ring-slate-100 sm:max-w-[88%]">
            <div className="mb-2 flex items-center gap-2">
              <img src="/brri-logo.jpg" alt="" className="h-5 w-5 object-contain" aria-hidden />
              <p className="text-xs font-medium text-brri-green">BRRI সহায়ক</p>
            </div>
            <article className="whitespace-pre-wrap font-bengali text-[15px] leading-relaxed text-slate-800">
              {streamingText}
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-brri-green align-middle" />
            </article>
          </div>
        </div>
      )}

      {loading && !streamingText && (
        <div className="flex justify-start">
          <div className="rounded-2xl rounded-bl-md bg-white px-4 py-3 shadow-sm ring-1 ring-slate-100">
            <Loader label="চিন্তা করছি…" compact />
          </div>
        </div>
      )}

      {!loading && suggestions?.length > 0 && (
        <FollowUpSuggestions
          suggestions={suggestions}
          onSelect={onSuggestionClick}
          disabled={loading}
        />
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
