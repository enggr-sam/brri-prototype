import { useEffect, useRef } from "react";
import ChatBubble from "./ChatBubble.jsx";
import Loader from "./Loader.jsx";

export default function ChatWindow({ messages, loading, error }) {
  const scrollRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div
      ref={scrollRef}
      className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-y-contain px-4 py-4"
      style={{ WebkitOverflowScrolling: "touch" }}
    >
      {messages.length === 0 && !loading && (
        <div className="flex min-h-[200px] flex-col items-center justify-center py-8 text-center text-slate-400">
          <div className="mb-2 text-4xl">🛠️</div>
          <p className="font-bengali text-sm">
            স্বাগতম! BRRI Winnower ২০২৪-এর সমস্যা বলুন — ছবি, কণ্ঠ, বা লেখা।
          </p>
          <p className="mt-1 text-xs">উত্তর বাংলায়, সংক্ষিপ্ত ও ধাপে ধাপে।</p>
        </div>
      )}

      {messages.map((msg) => (
        <ChatBubble key={msg.id ?? `${msg.role}-${msg.created_at}`} message={msg} />
      ))}

      {loading && (
        <div className="flex justify-start">
          <div className="rounded-2xl rounded-bl-md bg-white px-4 py-3 shadow-sm ring-1 ring-slate-100">
            <Loader label="চিন্তা করছি…" compact />
          </div>
        </div>
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
