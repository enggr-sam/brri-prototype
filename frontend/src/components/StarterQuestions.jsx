export const STARTER_QUESTIONS = [
  "Winnower কীভাবে কাজ করে? ধাপে ধাপে বলুন।",
  "চালু করার আগে কী কী দেখতে হবে?",
  "B65 বেল্ট কোথায় পাওয়া যাবে?",
  "কোন চালুনি কোন ফসলে লাগে?",
  "হপারে ধান আটকে যায় কেন?",
  "ব্লোয়ারের হাওয়া দুর্বল কেন?",
  "নিয়মিত রক্ষণাবেক্ষণ কীভাবে করব?",
  "Winnower-এর complete assembly drawing দেখান।",
  "ফ্রেম কোন ম্যাটেরিয়ালের, মাপ কত?",
  "মোটর গরম হলে কী করব?",
];

export default function StarterQuestions({ onSelect, disabled, compact = false }) {
  const items = compact ? STARTER_QUESTIONS.slice(0, 5) : STARTER_QUESTIONS;

  return (
    <div className={compact ? "" : "mb-4"}>
      <p className="mb-2 font-bengali text-xs text-slate-500">
        অথবা এখান থেকে শুরু করুন:
      </p>
      <div className="flex flex-col gap-2">
        {items.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(q)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left font-bengali text-xs leading-snug text-slate-700 shadow-sm transition hover:border-leaf-500/40 hover:bg-blue-50 disabled:opacity-40"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
