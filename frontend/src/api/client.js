const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000") + "/api/v1";
const REQUEST_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 15000);

let authHandlers = {
  onUnauthorized: null,
  onBlocked: null,
};

export class ApiError extends Error {
  constructor(message, { code = "API_ERROR", status = 500, details = {} } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export function setApiAuthHandlers(handlers) {
  authHandlers = {
    onUnauthorized: handlers?.onUnauthorized || null,
    onBlocked: handlers?.onBlocked || null,
  };
}

function parseApiError(payload, status) {
  const error = payload?.error || {};
  return new ApiError(error.message || "Request failed", {
    code: error.code || "API_ERROR",
    status,
    details: error.details || {},
  });
}

export async function apiRequest(path, { method = "GET", token, body, signal, skipAuthInterceptor = false } = {}) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  if (signal) {
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timeoutId);
    if (error?.name === "AbortError") {
      throw new ApiError("Request timed out", {
        code: "REQUEST_TIMEOUT",
        status: 408,
      });
    }
    throw new ApiError("Network request failed", {
      code: "NETWORK_ERROR",
      status: 0,
    });
  }
  clearTimeout(timeoutId);

  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const err = parseApiError(payload, response.status);

    if (!skipAuthInterceptor) {
      if (err.code === "AUTH_USER_BLOCKED" && typeof authHandlers.onBlocked === "function") {
        authHandlers.onBlocked(err);
      } else if ((response.status === 401 || response.status === 403) && typeof authHandlers.onUnauthorized === "function") {
        authHandlers.onUnauthorized(err);
      }
    }

    throw err;
  }

  return payload;
}

export function wsStreamUrl() {
  const fallback = "ws://localhost:8000";
  const configured = import.meta.env.VITE_WS_BASE_URL || fallback;
  return `${configured}/api/v1/stream`;
}

export function buildWsProtocols(token) {
  if (!token) {
    return ["gpuflow.v1"];
  }
  return ["gpuflow.v1", `bearer.${token}`];
}
