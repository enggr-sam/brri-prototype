import Header from "./Header.jsx";

export default function AppLayout({
  route,
  compactHeader = false,
  overlayHeader = false,
  children,
}) {
  // History stays off the marketing homepage; show it once someone is in a chat
  // session (compact) or already on the history page (with a way back via logo).
  const showHistory = route === "history" || compactHeader;

  return (
    <div
      className={`app-shell flex min-h-0 flex-1 flex-col overflow-hidden ${
        overlayHeader ? "relative" : ""
      }`}
    >
      <Header
        compact={compactHeader}
        overlay={overlayHeader}
        showHistory={showHistory && route !== "history"}
        showChatHome={route === "history"}
      />
      {children}
    </div>
  );
}
