import { useEffect, useState } from "react";
import AppLayout from "./components/AppLayout.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

function getRoute() {
  return window.location.hash === "#/history" ? "history" : "chat";
}

export default function App() {
  const [route, setRoute] = useState(getRoute);
  const [chatCompact, setChatCompact] = useState(false);
  const [showHero, setShowHero] = useState(true);

  useEffect(() => {
    const onHashChange = () => {
      const next = getRoute();
      setRoute(next);
      if (next === "chat") {
        setChatCompact(false);
        setShowHero(true);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const overlayHeader = route === "chat" && showHero && !chatCompact;

  return (
    <AppLayout
      route={route}
      compactHeader={route === "history" || chatCompact}
      overlayHeader={overlayHeader}
    >
      {route === "history" ? (
        <HistoryPage />
      ) : (
        <ChatPage
          onCompactChange={(v) => {
            setChatCompact(v);
            if (v) setShowHero(false);
          }}
          onHeroVisibility={setShowHero}
        />
      )}
    </AppLayout>
  );
}
