import { apiRequest } from "./client";

export function loginRequest(payload) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: payload,
    skipAuthInterceptor: true,
  });
}

export function registerRequest(payload) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: payload,
    skipAuthInterceptor: true,
  });
}

export function meRequest(token) {
  return apiRequest("/auth/me", { token, skipAuthInterceptor: true });
}
