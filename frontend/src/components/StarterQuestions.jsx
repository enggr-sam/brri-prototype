export const STARTER_QUESTIONS = [
  "Winnower কীভাবে কাজ করে? ধাপে ধাপে বলুন।",
  "চালু করার আগে কী কী দেখতে হবে?",
  "B65 বেল্ট কোথায় পাওয়া যাবে?",
  "কোন চালনি কোন ফসলে লাগে?",
  "হপারে ধান আটকে যায় কেন?",
  "ব্লোয়ারের হাওয়া দুর্বল কেন?",
  "নিয়মিত রক্ষণাবেক্ষণ কীভাবে করব?",
  "Winnower-এর complete assembly drawing দেখান।",
  "ফ্রেম কোন ম্যাটেরিয়ালের, মাপ কত?",
  "মোটর গরম হলে কী করব?",
];

export default function StarterQuestions({ onSelect, disabled }) {
  return (
    <div className="mb-4">
      <p className="mb-2 font-bengali text-sm text-leaf-800/75">
        অথবা এখান থেকে শুরু করুন:
      </p>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {STARTER_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(q)}
            className="w-full border border-leaf-500/25 bg-white px-3 py-2.5 text-left font-bengali text-xs leading-snug text-leaf-950 transition hover:bg-leaf-50 disabled:opacity-40 sm:w-auto sm:py-1.5"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
