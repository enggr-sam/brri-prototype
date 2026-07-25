import { useEffect, useState } from "react";
import AppLayout from "./components/AppLayout.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

function getRoute() {
  return window.location.hash === "#/history" ? "history" : "chat";
}

export default function App() {
  const [route, setRoute] = useState(getRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return (
    <AppLayout route={route}>
      {route === "history" ? <HistoryPage /> : <ChatPage />}
    </AppLayout>
  );
}
