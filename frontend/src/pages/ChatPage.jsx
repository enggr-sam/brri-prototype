import { useCallback, useEffect, useState } from "react";
import ChatInput from "../components/ChatInput.jsx";
import ChatSidebar from "../components/ChatSidebar.jsx";
import ChatWindow from "../components/ChatWindow.jsx";
import StarterQuestions from "../components/StarterQuestions.jsx";
import { fetchChatHistory, fetchChatSessions, logoutUser, sendChatMessageStream } from "../services/api.js";
import { clearAuth, getToken, getUser } from "../utils/auth.js";
import { formatSessionCostLabel } from "../utils/formatCost.js";
import { goTo, handleAppLink } from "../utils/nav.js";

export default function ChatPage() {
  const [user, setUser] = useState(() => getUser());
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streamingText, setStreamingText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionCostUsd, setSessionCostUsd] = useState(0);
  const [pendingSuggestions, setPendingSuggestions] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isEmpty = messages.length === 0 && !loading && !streamingText;

  const redirectToLogin = useCallback(() => {
    goTo("/login?next=/winnower");
  }, []);

  useEffect(() => {
    if (!getToken()) {
      redirectToLogin();
    }
  }, [redirectToLogin]);

  const loadSessions = useCallback(async () => {
    if (!getToken()) return;
    setSessionsLoading(true);
    try {
      const data = await fetchChatSessions({ limit: 80 });
      setSessions(data.sessions || []);
    } catch (err) {
      if (err.status === 401) {
        redirectToLogin();
        return;
      }
      setError(err.message || "ইতিহাস লোড করা যায়নি।");
    } finally {
      setSessionsLoading(false);
    }
  }, [redirectToLogin]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleSend = useCallback(
    async ({ text, imageFile, audioBlob, audioFilename }) => {
      if (!getToken()) {
        redirectToLogin();
        return;
      }
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
              loadSessions();
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
        if (err.status === 401) {
          redirectToLogin();
          return;
        }
        setError(err.message || "Something went wrong.");
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loadSessions, redirectToLogin]
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
    setSidebarOpen(false);
  };

  const openSession = async (id) => {
    if (loading) return;
    setSidebarOpen(false);
    if (id === sessionId && messages.length > 0) return;
    setError(null);
    setStreamingText("");
    setPendingSuggestions([]);
    try {
      const data = await fetchChatHistory(id);
      setSessionId(data.session_id);
      setMessages(data.messages || []);
      setSessionCostUsd(data.session_total_cost_usd || 0);
      const lastAssistant = [...(data.messages || [])]
        .reverse()
        .find((m) => m.role === "assistant");
      setPendingSuggestions(lastAssistant?.follow_up_suggestions || []);
    } catch (err) {
      if (err.status === 401) {
        redirectToLogin();
        return;
      }
      setError(err.message || "কথোপকথন খোলা যায়নি।");
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch {
      /* token is cleared locally anyway */
    }
    clearAuth();
    setUser(null);
    goTo("/");
  };

  return (
    <main className="flex min-h-0 flex-1 overflow-hidden bg-slate-100">
      {sidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-leaf-950/40 md:hidden"
          aria-label="সাইডবার বন্ধ"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div
        className={`fixed inset-y-0 left-0 z-40 w-[min(20rem,86vw)] transform transition-transform duration-200 md:static md:z-0 md:w-72 md:translate-x-0 lg:w-80 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <ChatSidebar
          user={user}
          sessions={sessions}
          activeId={sessionId}
          loading={sessionsLoading}
          onSelect={openSession}
          onNewChat={newChat}
          onLogout={handleLogout}
          onClose={() => setSidebarOpen(false)}
        />
      </div>

      <section className="flex min-h-0 min-w-0 flex-1 flex-col bg-white md:border-l md:border-slate-200">
        <header className="flex shrink-0 items-center justify-between border-b border-slate-100 px-3 py-2.5 sm:px-5">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="flex h-9 w-9 items-center justify-center text-leaf-800 md:hidden"
              aria-label="চ্যাট ইতিহাস"
            >
              <MenuIcon />
            </button>
            <a
              href="/"
              onClick={(e) => handleAppLink(e, "/")}
              className="hidden h-9 w-9 items-center justify-center text-leaf-500 hover:bg-leaf-50 sm:flex"
              aria-label="হোমে ফিরুন"
            >
              <CloseIcon />
            </a>
            <div className="min-w-0">
              <p className="truncate font-display text-sm font-semibold text-slate-800 sm:text-base">
                BRRI সহায়ক
              </p>
              <p className="truncate font-bengali text-[11px] text-slate-400">
                {loading ? "উত্তর লিখছে…" : "ব্রি শস্য ঝাড়াই যন্ত্র · ওয়েব ও মোবাইল"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={newChat}
              className="hidden font-bengali text-xs text-leaf-800/70 hover:text-leaf-950 sm:inline"
            >
              নতুন চ্যাট
            </button>
            <a
              href="/"
              onClick={(e) => handleAppLink(e, "/")}
              className="flex h-9 w-9 items-center justify-center text-leaf-500 hover:bg-leaf-50 sm:hidden"
              aria-label="হোমে ফিরুন"
            >
              <CloseIcon />
            </a>
          </div>
        </header>

        <div className="flex shrink-0 items-center gap-2.5 border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-slate-600 sm:px-6">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-leaf-500/10 text-leaf-500">
            <ChatGlyph />
          </span>
          <p className="min-w-0 truncate font-bengali text-sm">
            {sessionId ? "চলমান কথোপকথন" : "নতুন কথোপকথন"}
          </p>
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

        <div className="mx-auto w-full max-w-3xl">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>

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
      </section>
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
      <p className="font-bengali text-[15px] leading-relaxed text-slate-700 sm:text-base">
        ব্রি শস্য ঝাড়াই যন্ত্র নিয়ে জিজ্ঞেস করুন — যন্ত্রাংশ, সমস্যা, নকশা বা
        রক্ষণাবেক্ষণ। কম্পিউটার বা ফোন — দুই জায়গাতেই চ্যাট ও ইতিহাস ব্যবহার করা যাবে।
      </p>
      <StarterQuestions onSelect={onSelect} disabled={disabled} compact />
    </div>
  );
}

function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
      <path
        d="M3 4.5h12M3 9h12M3 13.5h12"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
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
