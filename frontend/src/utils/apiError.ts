import axios from "axios";

type ValidationIssue = {
  loc?: unknown[];
  msg?: string;
  type?: string;
  ctx?: { min_length?: number; max_length?: number };
};

// Turns pydantic's terse validation output into a sentence a person can act on.
function describeIssue(issue: ValidationIssue, field: string): string {
  const label = field.charAt(0).toUpperCase() + field.slice(1);
  if (issue.type === "string_too_short" && issue.ctx?.min_length) {
    return `${label} must be at least ${issue.ctx.min_length} characters.`;
  }
  if (issue.type === "string_too_long" && issue.ctx?.max_length) {
    return `${label} must be at most ${issue.ctx.max_length} characters.`;
  }
  if (issue.type === "value_error" && issue.msg?.startsWith("value is not a valid email")) {
    return "Enter a valid email address.";
  }
  // Messages from our own validators arrive as "Value error, <sentence>".
  const message = (issue.msg || "Invalid value").replace(/^Value error,\s*/i, "");
  return /^[A-Z]/.test(message) && /[.!?]$/.test(message) ? message : `${label}: ${message}`;
}

export function getApiErrorMessage(error: unknown, fallback = "The request could not be completed."): string {
  if (!axios.isAxiosError(error)) return fallback;
  const detail: unknown = error.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((value) => {
      const issue = value as ValidationIssue;
      const rawField = Array.isArray(issue.loc) ? issue.loc.at(-1) : undefined;
      const field = typeof rawField === "string" ? rawField.replaceAll("_", " ") : "field";
      return describeIssue(issue, field);
    });
    if (messages.length) return messages.join(" ");
  }
  if (detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string") return detail.message;
  return fallback;
}

