import { useCallback, useState } from "react";
import Header from "./components/Header.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import ChatInput from "./components/ChatInput.jsx";
import { sendChatMessage } from "./services/api.js";

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSend = useCallback(
    async ({ text, imageFile, audioBlob, audioFilename }) => {
      setLoading(true);
      setError(null);
      try {
        const data = await sendChatMessage({
          sessionId,
          text,
          imageFile,
          audioBlob,
          audioFilename,
        });
        setSessionId(data.session_id);
        setMessages((prev) => [
          ...prev,
          data.user_message,
          data.assistant_message,
        ]);
      } catch (err) {
        setError(err.message || "Something went wrong.");
      } finally {
        setLoading(false);
      }
    },
    [sessionId]
  );

  const newChat = () => {
    setSessionId(null);
    setMessages([]);
    setError(null);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-50">
      <Header />

      <main className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-2 py-3 sm:px-4">
        <div className="mb-2 shrink-0 flex justify-end">
          <button
            type="button"
            onClick={newChat}
            className="text-xs text-slate-500 hover:text-brri-dark"
          >
            + নতুন কথোপকথন
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl bg-slate-100 shadow-sm ring-1 ring-slate-200">
          <ChatWindow messages={messages} loading={loading} error={null} />
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>

        {error && (
          <p className="mt-2 shrink-0 text-center text-sm text-red-600">{error}</p>
        )}
      </main>
    </div>
  );
}
