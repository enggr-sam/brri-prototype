import { clearAuth, getToken } from "../utils/auth.js";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function authHeaders(extra = {}) {
  const token = getToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : { ...extra };
}

async function handleResponse(res) {
  if (res.status === 401) {
    clearAuth();
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json();
}

function parseSseBlock(block) {
  const line = block.split("\n").find((l) => l.startsWith("data: "));
  if (!line) return null;
  try {
    return JSON.parse(line.slice(6));
  } catch {
    return null;
  }
}

export async function registerUser({ mobile, password }) {
  const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mobile, password }),
  });
  return handleResponse(res);
}

export async function loginUser({ mobile, password }) {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mobile, password }),
  });
  return handleResponse(res);
}

export async function fetchMe() {
  const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function logoutUser() {
  const res = await fetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (res.status === 401) {
    clearAuth();
    return { ok: true };
  }
  return handleResponse(res);
}

/**
 * Stream a chat message via SSE — calls onEvent for each server event.
 */
export async function sendChatMessageStream(
  { sessionId, text, imageFile, audioBlob, audioFilename = "recording.webm" },
  onEvent
) {
  const formData = new FormData();
  if (sessionId) formData.append("session_id", sessionId);
  if (text?.trim()) formData.append("text", text.trim());
  if (imageFile) formData.append("image", imageFile);
  if (audioBlob) formData.append("audio", audioBlob, audioFilename);

  const res = await fetch(`${API_BASE_URL}/api/chat/message/stream`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (res.status === 401) {
    clearAuth();
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const event = parseSseBlock(part);
      if (event) onEvent(event);
    }
  }

  if (buffer.trim()) {
    const event = parseSseBlock(buffer);
    if (event) onEvent(event);
  }
}

export async function fetchChatHistory(sessionId) {
  const res = await fetch(`${API_BASE_URL}/api/chat/${sessionId}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function fetchChatSessions({ limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const res = await fetch(`${API_BASE_URL}/api/chat/sessions/list?${params}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/** Prefix API base for image URLs returned by the backend. */
export function mediaUrl(path) {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${API_BASE_URL}${path}`;
}
