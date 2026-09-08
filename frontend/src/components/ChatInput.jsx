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
  const textRef = useRef(null);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  useEffect(() => {
    const el = textRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 112)}px`;
  }, [text]);

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
      const mime = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg";
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
      setError("মাইক্রোফোনের অনুমতি দিন।");
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
      audioFilename: audioBlob?.type?.includes("ogg")
        ? "recording.ogg"
        : "recording.webm",
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

  const canSend = Boolean(text.trim() || imageFile || audioBlob);

  return (
    <div className="composer shrink-0 border-t border-slate-200 bg-white px-3 pt-2.5 sm:px-4">
      {error && (
        <p className="mb-2 font-bengali text-xs text-red-700">{error}</p>
      )}

      {imagePreview && (
        <div className="mb-2 flex items-start gap-2">
          <img
            src={imagePreview}
            alt="Preview"
            className="h-14 w-14 object-cover sm:h-16 sm:w-auto"
          />
          <button
            type="button"
            onClick={clearImage}
            className="min-h-11 font-bengali text-xs text-slate-400 hover:text-red-700 sm:min-h-0"
          >
            সরান
          </button>
        </div>
      )}

      {audioBlob && (
        <div className="mb-2 flex items-center gap-2">
          <span className="font-bengali text-xs text-slate-600">
            🎙️ কণ্ঠ রেকর্ড প্রস্তুত
          </span>
          <button
            type="button"
            onClick={clearAudio}
            className="min-h-11 font-bengali text-xs text-slate-400 hover:text-red-700 sm:min-h-0"
          >
            সরান
          </button>
        </div>
      )}

      <div className="flex items-end gap-2">
        <textarea
          ref={textRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder="প্রশ্ন লিখুন…"
          rows={1}
          className="max-h-28 min-h-[44px] flex-1 resize-none bg-transparent py-2.5 font-bengali text-[15px] text-slate-800 placeholder:text-slate-400 focus:outline-none disabled:opacity-50"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !canSend}
          aria-label="পাঠান"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-leaf-500 text-white shadow-sm transition hover:bg-leaf-600 disabled:opacity-35"
        >
          <SendIcon />
        </button>
      </div>

      <div className="flex items-center gap-1 pb-1">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={disabled || isRecording}
          title="📷 ছবি পাঠান"
          aria-label="📷 ছবি পাঠান"
          className="flex h-9 w-9 items-center justify-center text-slate-400 transition hover:text-leaf-500 disabled:opacity-40"
        >
          <PhotoIcon />
        </button>
        <button
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={disabled}
          title={isRecording ? "রেকর্ড থামান" : "কণ্ঠ বার্তা"}
          aria-label={isRecording ? "রেকর্ড থামান" : "কণ্ঠ বার্তা"}
          className={`flex h-9 w-9 items-center justify-center transition disabled:opacity-40 ${
            isRecording
              ? "animate-soft-pulse text-red-600"
              : "text-slate-400 hover:text-leaf-500"
          }`}
        >
          {isRecording ? <StopIcon /> : <MicIcon />}
        </button>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => pickImage(e.target.files?.[0])}
      />
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M2.2 8.1 13.4 2.6c.5-.25.98.3.72.8L9.7 13.7c-.22.46-.9.42-1.06-.06L7.2 9.2 2.3 8.1c-.5-.14-.5-.74-.1-1Z"
        fill="currentColor"
      />
    </svg>
  );
}

function PhotoIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
      <rect x="2" y="4" width="14" height="11" rx="1.6" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="6.2" cy="8" r="1.3" fill="currentColor" />
      <path d="M2.8 13.2 7 9.6l2.4 2 2.2-2.6 3.4 4.2" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <rect x="5.5" y="1.8" width="5" height="8" rx="2.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M3.4 7.6a4.6 4.6 0 0 0 9.2 0M8 12.2v2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <rect x="2.5" y="2.5" width="9" height="9" rx="1.2" fill="currentColor" />
    </svg>
  );
}
