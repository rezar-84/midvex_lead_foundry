import type { ApiError } from "./types"

export class RequestError extends Error {
  status: number
  error: ApiError

  constructor(status: number, error: ApiError) {
    super(error.message)
    this.status = status
    this.error = error
  }
}

function cookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : ""
}

function redirectToAuth(error: ApiError): void {
  const next = encodeURIComponent(window.location.pathname + window.location.search)
  if (error.code === "mfa_required") {
    window.location.assign(`/mfa/verify/?next=${next}`)
  } else {
    window.location.assign(`/accounts/login/?next=${next}`)
  }
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === "object" && "error" in body) {
      return (body as { error: ApiError }).error
    }
    // django-ninja's built-in auth failure shape: {"detail": "Unauthorized"}
    if (body && typeof body === "object" && "detail" in body) {
      return { code: "unauthorized", message: String((body as { detail: unknown }).detail), fields: null }
    }
  } catch {
    // fall through to the generic error
  }
  return { code: "error", message: `Request failed (${response.status})`, fields: null }
}

export async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const method = options.method ?? "GET"
  const headers: Record<string, string> = { Accept: "application/json" }
  if (method !== "GET") {
    headers["X-CSRFToken"] = cookie("csrftoken")
  }
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json"
  }
  const response = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  if (response.status === 401) {
    const error = await parseError(response)
    redirectToAuth(error)
    throw new RequestError(response.status, error)
  }
  if (!response.ok) {
    throw new RequestError(response.status, await parseError(response))
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
}
