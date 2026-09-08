import { useEffect, useState } from "react";
import AppLayout from "./components/AppLayout.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";
import HomePage from "./pages/HomePage.jsx";

function getRoute() {
  const path = (window.location.pathname || "/").replace(/\/+$/, "") || "/";
  if (path === "/winnower") return "winnower";
  if (path === "/history") return "history";

  const hash = (window.location.hash || "#/").replace(/^#/, "") || "/";
  if (hash === "/winnower" || hash.startsWith("/winnower?")) return "winnower";
  if (hash === "/history" || hash.startsWith("/history?")) return "history";
  return "home";
}

export default function App() {
  const [route, setRoute] = useState(getRoute);

  useEffect(() => {
    const sync = () => setRoute(getRoute());
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  return (
    <AppLayout
      route={route}
      compactHeader={route === "history"}
      overlayHeader={route === "home"}
      hideHeader={route === "winnower"}
    >
      {route === "history" ? (
        <HistoryPage />
      ) : route === "winnower" ? (
        <ChatPage />
      ) : (
        <HomePage />
      )}
    </AppLayout>
  );
}
