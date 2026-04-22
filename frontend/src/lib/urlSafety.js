export function getSafeNotebookUrl(value) {
  if (!value || typeof value !== "string") return null;

  try {
    const parsed = new URL(value, window.location.origin);
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return null;
    }
    return parsed.toString();
  } catch {
    return null;
  }
}
