// Thin fetch wrapper. Base URL is empty in dev (Vite proxies /api etc. to :8080)
// and empty in prod too, since the SPA is served same-origin under /app by FastAPI.

export const API_BASE = "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new ApiError(res.status, await _detail(res, `GET ${path}`));
  return res.json() as Promise<T>;
}

// Pull FastAPI's {detail: "..."} out of an error response for a useful message.
async function _detail(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    if (body && typeof body.detail === "string") return body.detail;
  } catch {
    /* ignore */
  }
  return `${fallback} → ${res.status}`;
}

export async function apiSend<T>(
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  // FastAPI endpoints often declare a required Pydantic body even when all its
  // fields are optional; a bodyless POST then 422s. So for write methods we
  // always send a JSON object ({} when none given). DELETE stays bodyless.
  const sendBody = method !== "DELETE" ? (body ?? {}) : body;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: sendBody !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: sendBody !== undefined ? JSON.stringify(sendBody) : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, await _detail(res, `${method} ${path}`));
  // Some endpoints return 204 / empty bodies.
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
