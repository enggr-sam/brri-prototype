export default function FollowUpSuggestions({ suggestions, onSelect, disabled }) {
  if (!suggestions?.length) return null;

  return (
    <div className="mt-3 border-t border-leaf-900/10 pt-3">
      <p className="mb-2 font-bengali text-xs font-medium text-leaf-800/60">
        পরবর্তী প্রশ্ন:
      </p>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {suggestions.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(q)}
            className="w-full border border-leaf-500/25 bg-leaf-50 px-3 py-2.5 text-left font-bengali text-xs leading-snug text-leaf-950 transition hover:bg-leaf-100 disabled:opacity-40 sm:w-auto sm:py-1.5"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
