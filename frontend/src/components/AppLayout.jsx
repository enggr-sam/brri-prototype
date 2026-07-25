import Header from "./Header.jsx";

const linkClass = (active) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
    active
      ? "bg-white/20 text-white"
      : "text-white/80 hover:bg-white/10 hover:text-white"
  }`;

export default function AppLayout({ route, children }) {
  const isHistory = route === "history";

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-50">
      <Header />
      <nav className="shrink-0 border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-3xl gap-1 px-4 py-2 sm:px-6">
          <a href="#/" className={linkClass(!isHistory)}>
            চ্যাট
          </a>
          <a href="#/history" className={linkClass(isHistory)}>
            ইতিহাস
          </a>
        </div>
      </nav>
      {children}
    </div>
  );
}
