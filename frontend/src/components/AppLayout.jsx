import Header from "./Header.jsx";

export default function AppLayout({
  route,
  compactHeader = false,
  overlayHeader = false,
  hideHeader = false,
  children,
}) {
  return (
    <div
      className={`app-shell flex min-h-0 flex-1 flex-col overflow-hidden ${
        overlayHeader ? "relative" : ""
      }`}
    >
      {!hideHeader && (
        <Header
          compact={compactHeader}
          overlay={overlayHeader}
          showChatHome={route === "history"}
        />
      )}
      {children}
    </div>
  );
}
