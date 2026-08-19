import { useCallback, useRef, useState } from "react";
import ChatWindow from "../components/ChatWindow.jsx";
import ChatInput from "../components/ChatInput.jsx";
import MachineHero from "../components/MachineHero.jsx";
import { sendChatMessageStream } from "../services/api.js";
import { formatSessionCostLabel } from "../utils/formatCost.js";

export default function ChatPage({ onCompactChange, onHeroVisibility }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streamingText, setStreamingText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionCostUsd, setSessionCostUsd] = useState(0);
  const [pendingSuggestions, setPendingSuggestions] = useState([]);
  const inputAnchorRef = useRef(null);

  const isEmpty =
    messages.length === 0 && !loading && !streamingText;

  const setCompact = useCallback(
    (value) => {
      onCompactChange?.(value);
      onHeroVisibility?.(false);
    },
    [onCompactChange, onHeroVisibility]
  );

  const focusComposer = () => {
    inputAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    const field = inputAnchorRef.current?.querySelector("textarea");
    field?.focus();
  };

  const handleSend = useCallback(
    async ({ text, imageFile, audioBlob, audioFilename }) => {
      setLoading(true);
      setError(null);
      setStreamingText("");
      setPendingSuggestions([]);
      setCompact(true);

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
    [sessionId, setCompact]
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
    onCompactChange?.(false);
    onHeroVisibility?.(true);
  };

  return (
    <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {isEmpty ? (
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
          <div className="animate-fade-up">
            <MachineHero onStart={focusComposer} />
          </div>

          <div
            ref={inputAnchorRef}
            className="mx-auto w-full max-w-3xl px-3 pb-6 pt-5 sm:px-4"
          >
            <p className="mb-3 font-bengali text-sm text-leaf-800/75">
              নিচে লিখুন, ছবি দিন, বা কণ্ঠে বলুন — উত্তর বাংলায় আসবে।
            </p>
            <div className="chat-panel overflow-hidden shadow-sm">
              <ChatInput onSend={handleSend} disabled={loading} />
            </div>
          </div>
        </div>
      ) : (
        <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-2 py-3 sm:px-4">
          <div className="mb-2 flex shrink-0 items-center justify-between gap-2">
            <p className="font-bengali text-xs text-leaf-800/70">
              {formatSessionCostLabel(sessionCostUsd)}
            </p>
            <button
              type="button"
              onClick={newChat}
              className="font-bengali text-xs text-leaf-800/70 transition hover:text-leaf-950"
            >
              + নতুন কথোপকথন
            </button>
          </div>

          <div className="chat-panel flex min-h-0 flex-1 flex-col overflow-hidden shadow-sm">
            <ChatWindow
              messages={messages}
              streamingText={streamingText}
              loading={loading}
              error={null}
              suggestions={pendingSuggestions}
              onSuggestionClick={handleSuggestionClick}
            />
            <div ref={inputAnchorRef}>
              <ChatInput onSend={handleSend} disabled={loading} />
            </div>
          </div>

          {error && (
            <p className="mt-2 shrink-0 text-center font-bengali text-sm text-red-700">
              {error}
            </p>
          )}
        </div>
      )}
    </main>
  );
}
