export default function FollowUpSuggestions({ suggestions, onSelect, disabled }) {
  if (!suggestions?.length) return null;

  return (
    <div className="mt-1 border-t border-slate-100 pt-3 dark:border-slate-800">
      <p className="mb-2 font-bengali text-xs font-medium text-slate-400 dark:text-slate-500">
        ➡️ পরবর্তী প্রশ্ন:
      </p>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {suggestions.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(q)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left font-bengali text-xs leading-snug text-slate-700 shadow-sm transition hover:border-leaf-500/40 hover:bg-blue-50 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-leaf-400/50 dark:hover:bg-slate-700 sm:w-auto sm:py-1.5"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
