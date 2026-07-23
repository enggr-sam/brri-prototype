// Central API client for the BRRI Winnower backend.
// In dev, requests go through Vite's proxy (see vite.config.js). In prod,
// set VITE_API_BASE_URL to the deployed backend origin.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return res.json();
}

/**
 * Send an image (and optional text) to the vision troubleshooting endpoint.
 * @param {File|Blob} imageFile
 * @param {string} text
 */
export async function troubleshootVision(imageFile, text) {
  const formData = new FormData();
  formData.append("image", imageFile);
  if (text && text.trim()) formData.append("text", text.trim());

  const res = await fetch(`${API_BASE_URL}/api/troubleshoot/vision`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(res);
}

/**
 * Send a recorded audio blob to the voice troubleshooting endpoint.
 * @param {Blob} audioBlob
 * @param {string} filename
 */
export async function troubleshootVoice(audioBlob, filename = "recording.webm") {
  const formData = new FormData();
  formData.append("audio", audioBlob, filename);

  const res = await fetch(`${API_BASE_URL}/api/troubleshoot/voice`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(res);
}
