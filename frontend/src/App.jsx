import { useState } from "react";
import Header from "./components/Header.jsx";
import ImageUpload from "./components/ImageUpload.jsx";
import AudioRecorder from "./components/AudioRecorder.jsx";
import ResponseDisplay from "./components/ResponseDisplay.jsx";
import Loader from "./components/Loader.jsx";
import { troubleshootVision, troubleshootVoice } from "./services/api.js";

const TABS = [
  { id: "vision", label: "📷 Image", desc: "Upload a photo of the part" },
  { id: "voice", label: "🎙️ Voice", desc: "Describe the issue by voice" },
];

export default function App() {
  const [tab, setTab] = useState("vision");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const run = async (promise) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await promise;
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleImage = (file, text) => run(troubleshootVision(file, text));
  const handleAudio = (blob, name) => run(troubleshootVoice(blob, name));

  return (
    <div className="min-h-full">
      <Header />

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <div className="grid gap-6 md:grid-cols-2">
          {/* Input panel */}
          <section className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
            <div className="mb-5 flex gap-2 rounded-lg bg-slate-100 p-1">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  disabled={loading}
                  className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition ${
                    tab === t.id
                      ? "bg-white text-brri-dark shadow"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <p className="mb-4 text-sm text-slate-500">
              {TABS.find((t) => t.id === tab)?.desc}
            </p>

            {tab === "vision" ? (
              <ImageUpload onSubmit={handleImage} disabled={loading} />
            ) : (
              <AudioRecorder onSubmit={handleAudio} disabled={loading} />
            )}
          </section>

          {/* Output panel */}
          <section className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
            {loading && <Loader />}

            {!loading && error && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                <p className="font-semibold">Error</p>
                <p>{error}</p>
              </div>
            )}

            {!loading && !error && !result && (
              <div className="flex h-full min-h-[240px] flex-col items-center justify-center text-center text-slate-400">
                <div className="mb-2 text-4xl">🛠️</div>
                <p className="text-sm">
                  Your troubleshooting solution will appear here.
                </p>
              </div>
            )}

            {!loading && result && <ResponseDisplay result={result} />}
          </section>
        </div>

        <footer className="mt-10 text-center text-xs text-slate-400">
          BRRI Winnower Model 2024 · Powered by FastAPI + Google Gemini · Answers
          in Bengali
        </footer>
      </main>
    </div>
  );
}
