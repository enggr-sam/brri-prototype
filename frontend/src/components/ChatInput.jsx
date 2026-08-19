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

  return (
    <div className="composer shrink-0 border-t border-leaf-900/8 bg-white/95 p-2.5 sm:p-3">
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
            className="min-h-11 font-bengali text-xs text-leaf-800/60 hover:text-red-700 sm:min-h-0"
          >
            সরান
          </button>
        </div>
      )}

      {audioBlob && (
        <div className="mb-2 flex items-center gap-2">
          <span className="font-bengali text-xs text-leaf-800/80">
            🎙️ কণ্ঠ রেকর্ড প্রস্তুত
          </span>
          <button
            type="button"
            onClick={clearAudio}
            className="min-h-11 font-bengali text-xs text-leaf-800/60 hover:text-red-700 sm:min-h-0"
          >
            সরান
          </button>
        </div>
      )}

      <div className="flex items-end gap-1.5 sm:gap-2">
        <div className="flex shrink-0 gap-0.5 sm:gap-1">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={disabled || isRecording}
            title="ছবি পাঠান"
            aria-label="ছবি পাঠান"
            className="flex h-11 w-11 items-center justify-center text-lg leading-none transition hover:bg-leaf-100 disabled:opacity-40 sm:h-10 sm:w-10"
          >
            📷
          </button>
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={disabled}
            title={isRecording ? "রেকর্ড থামান" : "কণ্ঠ বার্তা"}
            aria-label={isRecording ? "রেকর্ড থামান" : "কণ্ঠ বার্তা"}
            className={`flex h-11 w-11 items-center justify-center text-lg leading-none transition hover:bg-leaf-100 disabled:opacity-40 sm:h-10 sm:w-10 ${
              isRecording ? "animate-soft-pulse text-red-600" : ""
            }`}
          >
            {isRecording ? "⏹️" : "🎙️"}
          </button>
        </div>

        <textarea
          ref={textRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder="বাংলায় সমস্যা লিখুন…"
          rows={1}
          className="max-h-28 min-h-[44px] flex-1 resize-none border border-leaf-900/10 bg-white px-3 py-2.5 text-sm font-bengali text-leaf-950 focus:border-leaf-500 focus:outline-none focus:ring-1 focus:ring-leaf-500 disabled:opacity-50 sm:min-h-[42px]"
        />

        <button
          type="button"
          onClick={submit}
          disabled={disabled || (!text.trim() && !imageFile && !audioBlob)}
          className="h-11 shrink-0 bg-leaf-500 px-3.5 font-bengali text-sm font-semibold text-white transition hover:bg-leaf-950 disabled:opacity-40 sm:h-auto sm:px-4 sm:py-2.5"
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
