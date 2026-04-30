export async function filesToPayload(fileList) {
  const files = Array.from(fileList ?? []);
  return Promise.all(
    files.map(async (file) => ({
      filename: file.webkitRelativePath || file.name,
      content: await file.text(),
    })),
  );
}

export function inferLanguageFromFilename(filename) {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".java")) {
    return "java";
  }
  if (lower.endsWith(".js") || lower.endsWith(".mjs") || lower.endsWith(".cjs")) {
    return "javascript";
  }
  if (lower.endsWith(".go")) {
    return "go";
  }
  return "python";
}

export function formatDuration(durationMs) {
  if (typeof durationMs !== "number") {
    return "-";
  }
  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }
  return `${(durationMs / 1000).toFixed(2)} s`;
}
