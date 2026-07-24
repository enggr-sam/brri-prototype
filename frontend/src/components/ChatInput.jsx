import { useEffect, useRef, useState } from "react";

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [error, setError] = useState(null);

  const fileRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const clearImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const clearAudio = () => setAudioBlob(null);

  const pickImage = (file) => {
    if (!file?.type.startsWith("image/")) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setAudioBlob(null);
  };

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/ogg";
      const rec = new MediaRecorder(stream, { mimeType: mime });
      recorderRef.current = rec;
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = () => {
        setAudioBlob(new Blob(chunksRef.current, { type: mime }));
        stream.getTracks().forEach((t) => t.stop());
      };
      rec.start();
      setIsRecording(true);
      clearImage();
    } catch {
      setError("Microphone permission denied.");
    }
  };

  const stopRecording = () => {
    recorderRef.current?.stop();
    setIsRecording(false);
  };

  const submit = () => {
    if (disabled) return;
    if (!text.trim() && !imageFile && !audioBlob) return;
    onSend({
      text: text.trim(),
      imageFile,
      audioBlob,
      audioFilename: audioBlob?.type?.includes("ogg") ? "recording.ogg" : "recording.webm",
    });
    setText("");
    clearImage();
    clearAudio();
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-slate-200 bg-white p-3">
      {error && <p className="mb-2 text-xs text-red-600">{error}</p>}

      {imagePreview && (
        <div className="mb-2 flex items-start gap-2">
          <img src={imagePreview} alt="Preview" className="h-16 rounded-lg object-cover" />
          <button type="button" onClick={clearImage} className="text-xs text-slate-500 hover:text-red-600">
            ✕ Remove
          </button>
        </div>
      )}

      {audioBlob && (
        <div className="mb-2 flex items-center gap-2">
          <span className="text-xs text-slate-600">🎙️ Voice ready</span>
          <button type="button" onClick={clearAudio} className="text-xs text-slate-500 hover:text-red-600">
            ✕ Remove
          </button>
        </div>
      )}

      <div className="flex items-end gap-2">
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={disabled || isRecording}
            title="Photo"
            className="rounded-lg p-2 text-lg hover:bg-slate-100 disabled:opacity-40"
          >
            📷
          </button>
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={disabled}
            title="Voice"
            className={`rounded-lg p-2 text-lg hover:bg-slate-100 disabled:opacity-40 ${
              isRecording ? "animate-pulse text-red-600" : ""
            }`}
          >
            {isRecording ? "⏹" : "🎙️"}
          </button>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder="বাংলায় সমস্যা লিখুন… (Enter = পাঠান)"
          rows={1}
          className="max-h-28 min-h-[42px] flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm font-bengali focus:border-brri-green focus:outline-none focus:ring-1 focus:ring-brri-green disabled:opacity-50"
        />

        <button
          type="button"
          onClick={submit}
          disabled={disabled || (!text.trim() && !imageFile && !audioBlob)}
          className="rounded-xl bg-brri-green px-4 py-2.5 text-sm font-semibold text-white hover:bg-brri-dark disabled:opacity-40"
        >
          পাঠান
        </button>

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => pickImage(e.target.files?.[0])}
        />
      </div>
    </div>
  );
}
