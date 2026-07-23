import { useCallback, useRef, useState } from "react";

/**
 * Drag-and-drop + click-to-select image uploader with a live preview and an
 * optional text description. Calls `onSubmit(file, text)` when the user submits.
 */
export default function ImageUpload({ onSubmit, disabled }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [text, setText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const selectFile = useCallback((selected) => {
    if (!selected) return;
    if (!selected.type.startsWith("image/")) {
      alert("Please select an image file.");
      return;
    }
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      selectFile(e.dataTransfer.files?.[0]);
    },
    [disabled, selectFile]
  );

  const clear = () => {
    setFile(null);
    setPreviewUrl(null);
    setText("");
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleSubmit = () => {
    if (file && !disabled) onSubmit(file, text);
  };

  return (
    <div className="space-y-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition ${
          isDragging
            ? "border-brri-green bg-brri-light"
            : "border-slate-300 bg-slate-50 hover:border-brri-green"
        } ${disabled ? "pointer-events-none opacity-60" : ""}`}
      >
        {previewUrl ? (
          <img
            src={previewUrl}
            alt="Selected part preview"
            className="max-h-56 rounded-lg object-contain shadow"
          />
        ) : (
          <>
            <div className="mb-2 text-4xl">📷</div>
            <p className="font-medium text-slate-700">
              Drag &amp; drop a photo of the part here
            </p>
            <p className="text-sm text-slate-500">or click to browse</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => selectFile(e.target.files?.[0])}
        />
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        placeholder="Optional: describe the problem (English or Bengali)..."
        rows={3}
        className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-brri-green focus:outline-none focus:ring-1 focus:ring-brri-green disabled:opacity-60"
      />

      <div className="flex gap-3">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!file || disabled}
          className="flex-1 rounded-lg bg-brri-green px-4 py-2.5 font-semibold text-white transition hover:bg-brri-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          Analyze Image
        </button>
        {file && (
          <button
            type="button"
            onClick={clear}
            disabled={disabled}
            className="rounded-lg border border-slate-300 px-4 py-2.5 font-medium text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}
