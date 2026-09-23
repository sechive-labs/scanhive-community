function parseApiTimestamp(timestamp: string): Date {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(timestamp);

  return new Date(hasTimezone ? timestamp : `${timestamp}Z`);
}

export function formatRelativeTime(
  timestamp: string | null,
  now: number,
): string {
  if (!timestamp) {
    return "Not scanned";
  }

  const timestampMs = parseApiTimestamp(timestamp).getTime();

  if (Number.isNaN(timestampMs)) {
    return "Unknown";
  }

  const elapsedSeconds = Math.max(
    0,
    Math.floor((now - timestampMs) / 1000),
  );

  if (elapsedSeconds < 60) {
    return "Just now";
  }

  const elapsedMinutes = Math.floor(elapsedSeconds / 60);

  if (elapsedMinutes < 60) {
    return `${elapsedMinutes} ${
      elapsedMinutes === 1 ? "minute" : "minutes"
    } ago`;
  }

  const elapsedHours = Math.floor(elapsedMinutes / 60);

  if (elapsedHours < 24) {
    return `${elapsedHours} ${
      elapsedHours === 1 ? "hour" : "hours"
    } ago`;
  }

  const elapsedDays = Math.floor(elapsedHours / 24);

  return `${elapsedDays} ${
    elapsedDays === 1 ? "day" : "days"
  } ago`;
}

export function formatLocalDateTime(
  timestamp: string | null,
): string | undefined {
  if (!timestamp) {
    return undefined;
  }

  const date = parseApiTimestamp(timestamp);

  if (Number.isNaN(date.getTime())) {
    return undefined;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
