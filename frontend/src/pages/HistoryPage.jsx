import { useCallback, useEffect, useState } from "react";
import ChatBubble from "../components/ChatBubble.jsx";
import Loader from "../components/Loader.jsx";
import { fetchChatHistory, fetchChatSessions } from "../services/api.js";
import { formatDateTime } from "../utils/formatTime.js";

function SessionCard({ session, expanded, onToggle, detail, loadingDetail }) {
  return (
    <article className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-start gap-3 px-4 py-4 text-left hover:bg-slate-50"
        aria-expanded={expanded}
      >
        <span
          className={`mt-1 shrink-0 text-slate-400 transition-transform ${
            expanded ? "rotate-90" : ""
          }`}
          aria-hidden
        >
          ▶
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <time dateTime={session.last_message_at}>
              {formatDateTime(session.last_message_at)}
            </time>
            <span className="rounded bg-slate-100 px-1.5 py-0.5">
              {session.message_count} বার্তা
            </span>
          </div>
          <p className="mt-1 font-bengali text-sm leading-relaxed text-slate-800 line-clamp-2">
            {session.preview}
          </p>
          <p className="mt-1 truncate font-mono text-[10px] text-slate-400">
            {session.session_id}
          </p>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-100 bg-slate-50 px-4 py-4">
          <p className="mb-3 text-xs text-slate-500">
            শুরু: {formatDateTime(session.started_at)}
          </p>
          {loadingDetail && (
            <Loader label="কথোপকথন লোড হচ্ছে…" compact />
          )}
          {!loadingDetail && detail?.messages?.length > 0 && (
            <div className="space-y-4">
              {detail.messages.map((msg) => (
                <div key={msg.id}>
                  <p className="mb-1 text-center text-[11px] text-slate-400">
                    {formatDateTime(msg.created_at)}
                    {msg.role === "user" ? " · প্রশ্ন" : " · উত্তর"}
                  </p>
                  <ChatBubble message={msg} showTimestamp={false} />
                </div>
              ))}
            </div>
          )}
          {!loadingDetail && detail && detail.messages.length === 0 && (
            <p className="text-sm text-slate-500">কোনো বার্তা নেই।</p>
          )}
        </div>
      )}
    </article>
  );
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [details, setDetails] = useState({});
  const [loadingDetailId, setLoadingDetailId] = useState(null);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchChatSessions({ limit: 100 });
      setSessions(data.sessions);
      setTotal(data.total);
    } catch (err) {
      setError(err.message || "ইতিহাস লোড করা যায়নি।");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const toggleSession = async (sessionId) => {
    if (expandedId === sessionId) {
      setExpandedId(null);
      return;
    }

    setExpandedId(sessionId);

    if (details[sessionId]) return;

    setLoadingDetailId(sessionId);
    try {
      const data = await fetchChatHistory(sessionId);
      setDetails((prev) => ({ ...prev, [sessionId]: data }));
    } catch (err) {
      setError(err.message || "কথোপকথন লোড করা যায়নি।");
      setExpandedId(null);
    } finally {
      setLoadingDetailId(null);
    }
  };

  return (
    <main className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-2 py-3 sm:px-4">
      <div className="mb-3 shrink-0 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-brri-dark">কথোপকথনের ইতিহাস</h2>
          <p className="text-xs text-slate-500">
            সব সেশন · সময় ও প্রশ্ন-উত্তর সহ
          </p>
        </div>
        <button
          type="button"
          onClick={loadSessions}
          disabled={loading}
          className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          ↻ রিফ্রেশ
        </button>
      </div>

      <div
        className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-y-contain pb-4"
        style={{ WebkitOverflowScrolling: "touch" }}
      >
        {loading && (
          <div className="py-12">
            <Loader label="ইতিহাস লোড হচ্ছে…" />
          </div>
        )}

        {!loading && error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && sessions.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white py-16 text-center text-slate-400">
            <p className="font-bengali text-sm">এখনো কোনো কথোপকথন নেই।</p>
          </div>
        )}

        {!loading &&
          sessions.map((session) => (
            <SessionCard
              key={session.session_id}
              session={session}
              expanded={expandedId === session.session_id}
              onToggle={() => toggleSession(session.session_id)}
              detail={details[session.session_id]}
              loadingDetail={loadingDetailId === session.session_id}
            />
          ))}
      </div>

      {!loading && total > 0 && (
        <p className="shrink-0 pt-2 text-center text-xs text-slate-400">
          মোট {total}টি কথোপকথন · সর্বশেষ {sessions.length}টি দেখানো হচ্ছে
        </p>
      )}
    </main>
  );
}
