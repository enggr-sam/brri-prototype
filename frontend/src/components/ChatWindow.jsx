import { useEffect, useRef } from "react";
import ChatBubble from "./ChatBubble.jsx";
import FollowUpSuggestions from "./FollowUpSuggestions.jsx";
import Loader from "./Loader.jsx";
import MarkdownReply from "./MarkdownReply.jsx";

export default function ChatWindow({
  messages,
  streamingText,
  loading,
  error,
  suggestions,
  onSuggestionClick,
  emptySlot = null,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, loading]);

  return (
    <div
      className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 py-5 sm:px-6 lg:px-8"
      style={{ WebkitOverflowScrolling: "touch" }}
    >
      <div className="mx-auto w-full max-w-3xl space-y-5">
      {emptySlot}

      {messages.map((msg) => (
        <ChatBubble key={msg.id ?? `${msg.role}-${msg.created_at}`} message={msg} />
      ))}

      {streamingText && (
        <div className="flex items-start gap-2.5">
          <img
            src="/brri-logo.jpg"
            alt=""
            className="mt-0.5 h-8 w-8 shrink-0 rounded-full bg-slate-100 object-contain p-0.5"
            aria-hidden
          />
          <div className="min-w-0 flex-1 pt-0.5">
            <p className="mb-1 text-xs font-semibold text-slate-600">BRRI সহায়ক</p>
            <div className="relative">
              <MarkdownReply text={streamingText} className="text-slate-800" />
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-leaf-500 align-middle" />
            </div>
          </div>
        </div>
      )}

      {loading && !streamingText && (
        <div className="flex items-start gap-2.5">
          <img
            src="/brri-logo.jpg"
            alt=""
            className="mt-0.5 h-8 w-8 shrink-0 rounded-full bg-slate-100 object-contain p-0.5"
            aria-hidden
          />
          <div className="pt-1">
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
    </div>
  );
}
