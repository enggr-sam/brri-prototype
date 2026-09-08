import { useCallback, useState } from "react";
import ChatWindow from "../components/ChatWindow.jsx";
import ChatInput from "../components/ChatInput.jsx";
import StarterQuestions from "../components/StarterQuestions.jsx";
import { sendChatMessageStream } from "../services/api.js";
import { handleAppLink } from "../utils/nav.js";
import { formatSessionCostLabel } from "../utils/formatCost.js";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streamingText, setStreamingText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionCostUsd, setSessionCostUsd] = useState(0);
  const [pendingSuggestions, setPendingSuggestions] = useState([]);

  const isEmpty = messages.length === 0 && !loading && !streamingText;

  const handleSend = useCallback(
    async ({ text, imageFile, audioBlob, audioFilename }) => {
      setLoading(true);
      setError(null);
      setStreamingText("");
      setPendingSuggestions([]);

      const userPreview = {
        id: `pending-user-${Date.now()}`,
        role: "user",
        content: text || (imageFile ? "(ছবি পাঠানো)" : "(কণ্ঠ বার্তা)"),
        modality: imageFile ? "vision" : audioBlob ? "voice" : "text",
        attachment_url: null,
        reference_images: [],
        follow_up_suggestions: [],
        cost_usd: 0,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userPreview]);

      try {
        await sendChatMessageStream(
          { sessionId, text, imageFile, audioBlob, audioFilename },
          (event) => {
            if (event.type === "start") {
              setSessionId(event.session_id);
            } else if (event.type === "token") {
              setStreamingText((prev) => prev + event.text);
            } else if (event.type === "done") {
              setSessionId(event.session_id);
              setSessionCostUsd(event.session_total_cost_usd || 0);
              setStreamingText("");
              setMessages((prev) => {
                const withoutPending = prev.filter(
                  (m) => !String(m.id).startsWith("pending-")
                );
                return [
                  ...withoutPending,
                  event.user_message,
                  event.assistant_message,
                ];
              });
              setPendingSuggestions(
                event.assistant_message?.follow_up_suggestions || []
              );
            } else if (event.type === "error") {
              throw new Error(event.detail || "AI service error.");
            }
          }
        );
      } catch (err) {
        setMessages((prev) =>
          prev.filter((m) => !String(m.id).startsWith("pending-"))
        );
        setStreamingText("");
        setError(err.message || "Something went wrong.");
      } finally {
        setLoading(false);
      }
    },
    [sessionId]
  );

  const handleSuggestionClick = (question) => {
    if (loading) return;
    handleSend({ text: question });
  };

  const newChat = () => {
    setSessionId(null);
    setMessages([]);
    setStreamingText("");
    setError(null);
    setSessionCostUsd(0);
    setPendingSuggestions([]);
  };

  return (
    <main className="flex min-h-0 flex-1 flex-col overflow-hidden bg-[#f4f6f5]">
      <div className="mx-auto flex min-h-0 w-full max-w-lg flex-1 flex-col bg-white shadow-sm sm:my-3 sm:max-w-xl sm:overflow-hidden sm:rounded-2xl sm:border sm:border-leaf-900/8">
        <header className="flex shrink-0 items-center justify-between border-b border-slate-100 px-4 py-3">
          <a
            href="/"
            onClick={(e) => handleAppLink(e, "/")}
            className="flex h-8 w-8 items-center justify-center text-leaf-500 transition hover:bg-leaf-50"
            aria-label="হোমে ফিরুন"
          >
            <CloseIcon />
          </a>
          <h1 className="font-display text-sm font-semibold tracking-wide text-slate-800">
            চ্যাট
          </h1>
          <a
            href="/history"
            onClick={(e) => handleAppLink(e, "/history")}
            className="font-bengali text-xs text-leaf-800/60 hover:text-leaf-950"
          >
            ইতিহাস
          </a>
        </header>

        <div className="flex shrink-0 items-center justify-between bg-leaf-950 px-4 py-2.5 text-white">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/10">
              <ChatGlyph />
            </span>
            <div className="min-w-0">
              <p className="truncate font-bengali text-sm font-medium">
                BRRI সহায়ক
              </p>
              <p className="truncate font-bengali text-[11px] text-white/65">
                {loading ? "উত্তর লিখছে…" : "লাইভ · ব্রি শস্য ঝাড়াই যন্ত্র"}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={newChat}
            className="shrink-0 font-bengali text-xs text-white/75 hover:text-white"
          >
            নতুন
          </button>
        </div>

        <ChatWindow
          messages={messages}
          streamingText={streamingText}
          loading={loading}
          error={null}
          suggestions={pendingSuggestions}
          onSuggestionClick={handleSuggestionClick}
          emptySlot={
            isEmpty ? (
              <EmptyThread
                onSelect={handleSuggestionClick}
                disabled={loading}
              />
            ) : null
          }
        />

        <ChatInput onSend={handleSend} disabled={loading} />

        {(error || sessionCostUsd > 0) && (
          <div className="shrink-0 px-4 pb-2">
            {error && (
              <p className="text-center font-bengali text-sm text-red-700">
                {error}
              </p>
            )}
            {!error && sessionCostUsd > 0 && (
              <p className="text-center font-bengali text-[10px] text-slate-400">
                {formatSessionCostLabel(sessionCostUsd)}
              </p>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

function EmptyThread({ onSelect, disabled }) {
  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <img
          src="/brri-logo.jpg"
          alt=""
          className="mt-0.5 h-8 w-8 rounded-full bg-slate-100 object-contain p-0.5"
          aria-hidden
        />
        <div>
          <p className="text-sm font-semibold text-slate-700">BRRI সহায়ক</p>
          <p className="font-bengali text-xs text-slate-400">প্রস্তুত</p>
        </div>
      </div>
      <p className="text-center font-bengali text-[11px] text-slate-400">
        চ্যাট শুরু ·{" "}
        {new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Asia/Dhaka",
        })}
      </p>
      <p className="font-bengali text-[15px] leading-relaxed text-slate-700">
        ব্রি শস্য ঝাড়াই যন্ত্র নিয়ে জিজ্ঞেস করুন — যন্ত্রাংশ, সমস্যা, নকশা বা
        রক্ষণাবেক্ষণ। নিচে লিখুন, ছবি দিন, বা একটি প্রশ্ন বেছে নিন।
      </p>
      <StarterQuestions onSelect={onSelect} disabled={disabled} compact />
    </div>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M3.5 3.5l9 9M12.5 3.5l-9 9"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ChatGlyph() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M3 3.5h10a1 1 0 0 1 1 1V10a1 1 0 0 1-1 1H7l-3 2v-2H3a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}
