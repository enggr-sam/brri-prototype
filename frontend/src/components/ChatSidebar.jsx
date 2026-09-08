import { formatDateTime } from "../utils/formatTime.js";

export default function ChatSidebar({
  user,
  sessions,
  activeId,
  loading,
  onSelect,
  onNewChat,
  onLogout,
  onClose,
}) {
  return (
    <aside className="flex h-full min-h-0 w-full flex-col bg-leaf-950 text-white">
      <div className="flex shrink-0 items-center justify-between gap-2 px-4 py-4">
        <div className="min-w-0">
          <p className="font-display text-sm font-semibold tracking-tight">
            BRRI সহায়ক
          </p>
          <p className="truncate font-bengali text-xs text-white/55">
            {user?.mobile ? `👤 ${user.mobile}` : "🔐 লগইন করা"}
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white md:hidden"
            aria-label="সাইডবার বন্ধ"
          >
            ×
          </button>
        )}
      </div>

      <div className="shrink-0 px-3 pb-3">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full rounded-lg bg-leaf-500 px-3 py-2 font-bengali text-sm font-semibold text-white shadow-sm transition hover:bg-leaf-600"
        >
          ✨ নতুন চ্যাট
        </button>
      </div>

      <div
        className="min-h-0 flex-1 space-y-1 overflow-y-auto px-2 pb-3"
        style={{ WebkitOverflowScrolling: "touch" }}
      >
        {loading && (
          <p className="px-2 py-4 font-bengali text-xs text-white/50">
            📂 ইতিহাস লোড হচ্ছে…
          </p>
        )}
        {!loading && sessions.length === 0 && (
          <p className="px-2 py-4 font-bengali text-xs text-white/50">
            💬 এখনো কোনো কথোপকথন নেই।
          </p>
        )}
        {sessions.map((session) => {
          const active = session.session_id === activeId;
          return (
            <button
              key={session.session_id}
              type="button"
              onClick={() => onSelect(session.session_id)}
              className={`w-full rounded-lg px-3 py-2.5 text-left transition ${
                active ? "bg-leaf-500 text-white" : "hover:bg-white/10"
              }`}
            >
              <p className="line-clamp-2 font-bengali text-[13px] leading-snug text-white/95">
                {session.preview}
              </p>
              <p className="mt-1 font-bengali text-[11px] text-white/50">
                {formatDateTime(session.last_message_at)} · {session.message_count} বার্তা
              </p>
            </button>
          );
        })}
      </div>

      <div className="shrink-0 border-t border-white/10 px-3 py-3">
        <button
          type="button"
          onClick={onLogout}
          className="w-full rounded-lg px-3 py-2 text-left font-bengali text-sm text-white/70 hover:bg-white/10 hover:text-white"
        >
          🚪 লগআউট
        </button>
      </div>
    </aside>
  );
}
