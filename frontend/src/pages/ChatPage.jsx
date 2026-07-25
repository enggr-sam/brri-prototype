import { useCallback, useState } from "react";
import ChatWindow from "../components/ChatWindow.jsx";
import ChatInput from "../components/ChatInput.jsx";
import { sendChatMessageStream } from "../services/api.js";
import { formatSessionCostLabel } from "../utils/formatCost.js";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streamingText, setStreamingText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionCostUsd, setSessionCostUsd] = useState(0);
  const [pendingSuggestions, setPendingSuggestions] = useState([]);

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
              setPendingSuggestions(event.assistant_message?.follow_up_suggestions || []);
            } else if (event.type === "error") {
              throw new Error(event.detail || "AI service error.");
            }
          }
        );
      } catch (err) {
        setMessages((prev) => prev.filter((m) => !String(m.id).startsWith("pending-")));
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
    <main className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-2 py-3 sm:px-4">
      <div className="mb-2 shrink-0 flex items-center justify-between gap-2">
        <p className="font-bengali text-xs text-slate-500">
          {formatSessionCostLabel(sessionCostUsd)}
        </p>
        <button
          type="button"
          onClick={newChat}
          className="text-xs text-slate-500 hover:text-brri-dark"
        >
          + নতুন কথোপকথন
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl bg-slate-100 shadow-sm ring-1 ring-slate-200">
        <ChatWindow
          messages={messages}
          streamingText={streamingText}
          loading={loading}
          error={null}
          suggestions={pendingSuggestions}
          onSuggestionClick={handleSuggestionClick}
        />
        <ChatInput onSend={handleSend} disabled={loading} />
      </div>

      {error && (
        <p className="mt-2 shrink-0 text-center text-sm text-red-600">{error}</p>
      )}
    </main>
  );
}
