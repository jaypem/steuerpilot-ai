/**
 * Parses a `text/event-stream` ReadableStream into an async iterable of
 * typed JSON payloads. Only `data:` lines are processed; comments and
 * empty lines are silently skipped.
 */
export async function* parseSSEStream<T>(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<T> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Split on newlines; keep the incomplete tail in the buffer
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trimEnd();
        if (trimmed.startsWith("data: ")) {
          const json = trimmed.slice(6).trim();
          if (json) yield JSON.parse(json) as T;
        }
      }
    }

    // Flush any remaining data after the stream closes
    const remaining = buffer.trimEnd();
    if (remaining.startsWith("data: ")) {
      const json = remaining.slice(6).trim();
      if (json) yield JSON.parse(json) as T;
    }
  } finally {
    reader.releaseLock();
  }
}
