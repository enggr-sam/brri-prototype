export default function Loader({ label = "Analyzing with Gemini..." }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-10">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-brri-light border-t-brri-green" />
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <div className="w-full max-w-md space-y-2">
        <div className="h-3 w-full animate-pulse rounded bg-slate-200" />
        <div className="h-3 w-5/6 animate-pulse rounded bg-slate-200" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-slate-200" />
      </div>
    </div>
  );
}
