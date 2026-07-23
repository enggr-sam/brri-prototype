import { useEffect, useRef, useState } from "react";

/**
 * Captures the user's voice via the browser MediaRecorder API, shows a live
 * timer + playback, and submits the recorded Blob via `onSubmit(blob, name)`.
 */
export default function AudioRecorder({ onSubmit, disabled }) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const blobRef = useRef(null);
  const timerRef = useRef(null);

  // Cleanup on unmount: stop tracks and clear timers.
  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      // Pick a mime type the browser actually supports.
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        blobRef.current = blob;
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setIsRecording(true);
      setAudioUrl(null);
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (err) {
      setError(
        "Microphone access denied or unavailable. Please allow mic permission."
      );
      console.error(err);
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    clearInterval(timerRef.current);
  };

  const handleSubmit = () => {
    if (blobRef.current && !disabled) {
      const ext = blobRef.current.type.includes("ogg") ? "ogg" : "webm";
      onSubmit(blobRef.current, `recording.${ext}`);
    }
  };

  const reset = () => {
    setAudioUrl(null);
    setSeconds(0);
    blobRef.current = null;
  };

  const mmss = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(
    seconds % 60
  ).padStart(2, "0")}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-col items-center gap-4 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-8">
        <div className="text-4xl">{isRecording ? "🔴" : "🎙️"}</div>

        {isRecording ? (
          <div className="text-2xl font-mono font-bold text-red-600">{mmss}</div>
        ) : (
          <p className="text-sm text-slate-500">
            Tap record and describe the issue in your own words.
          </p>
        )}

        {!isRecording ? (
          <button
            type="button"
            onClick={startRecording}
            disabled={disabled}
            className="rounded-full bg-red-600 px-6 py-3 font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
          >
            {audioUrl ? "Re-record" : "Record Audio"}
          </button>
        ) : (
          <button
            type="button"
            onClick={stopRecording}
            className="rounded-full bg-slate-800 px-6 py-3 font-semibold text-white transition hover:bg-slate-900"
          >
            ⏹ Stop Recording
          </button>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {audioUrl && (
        <div className="space-y-3">
          <audio src={audioUrl} controls className="w-full" />
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={disabled}
              className="flex-1 rounded-lg bg-brri-green px-4 py-2.5 font-semibold text-white transition hover:bg-brri-dark disabled:opacity-50"
            >
              Analyze Audio
            </button>
            <button
              type="button"
              onClick={reset}
              disabled={disabled}
              className="rounded-lg border border-slate-300 px-4 py-2.5 font-medium text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
