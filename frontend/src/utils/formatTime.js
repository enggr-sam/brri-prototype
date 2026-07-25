/** Format ISO timestamps for display (Bangladesh time). */
export function formatDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("bn-BD", {
    timeZone: "Asia/Dhaka",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function modalityLabel(modality) {
  switch (modality) {
    case "vision":
      return "ছবি";
    case "voice":
      return "কণ্ঠ";
    default:
      return "লেখা";
  }
}
