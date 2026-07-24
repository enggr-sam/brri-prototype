const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

/**
 * Send a chat message (text, optional image, optional audio).
 * @param {{ sessionId?: string, text?: string, imageFile?: File, audioBlob?: Blob, audioFilename?: string }} opts
 */
export async function sendChatMessage({
  sessionId,
  text,
  imageFile,
  audioBlob,
  audioFilename = "recording.webm",
}) {
  const formData = new FormData();
  if (sessionId) formData.append("session_id", sessionId);
  if (text?.trim()) formData.append("text", text.trim());
  if (imageFile) formData.append("image", imageFile);
  if (audioBlob) formData.append("audio", audioBlob, audioFilename);

  const res = await fetch(`${API_BASE_URL}/api/chat/message`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(res);
}

export async function fetchChatHistory(sessionId) {
  const res = await fetch(`${API_BASE_URL}/api/chat/${sessionId}`);
  return handleResponse(res);
}

/** Prefix API base for image URLs returned by the backend. */
export function mediaUrl(path) {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${API_BASE_URL}${path}`;
}
