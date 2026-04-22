import { apiRequest } from "./client";

export function getUserDashboard(token) {
  return apiRequest("/dashboard/user", { token });
}

export function getAdminDashboard(token) {
  return apiRequest("/dashboard/admin", { token });
}

export function launchSession(token, profileId) {
  return apiRequest("/sessions/launch", {
    method: "POST",
    token,
    body: { profileId },
  });
}

export function cancelQueueItem(token, queueId) {
  return apiRequest(`/queue/${queueId}/cancel`, {
    method: "POST",
    token,
  });
}

export function relaunchSession(token, sessionId) {
  return apiRequest(`/sessions/${sessionId}/relaunch`, {
    method: "POST",
    token,
  });
}

export function getSessionAccess(token, sessionId) {
  return apiRequest(`/sessions/${sessionId}/access`, { token });
}

export function promoteQueueItem(token, queueId) {
  return apiRequest(`/admin/queue/${queueId}/promote`, {
    method: "POST",
    token,
  });
}

export function deleteQueueItem(token, queueId) {
  return apiRequest(`/admin/queue/${queueId}`, {
    method: "DELETE",
    token,
  });
}

export function warnSession(token, sessionId, message) {
  return apiRequest(`/admin/sessions/${sessionId}/warn`, {
    method: "POST",
    token,
    body: { message },
  });
}

export function terminateSession(token, sessionId) {
  return apiRequest(`/admin/sessions/${sessionId}/terminate`, {
    method: "POST",
    token,
  });
}

export function blockUser(token, userId) {
  return apiRequest(`/admin/users/${userId}/block`, {
    method: "POST",
    token,
  });
}

export function unblockUser(token, userId) {
  return apiRequest(`/admin/users/${userId}/unblock`, {
    method: "POST",
    token,
  });
}

export function updateUserLimits(token, userId, maxActiveSessions, maxQueuedRequests) {
  return apiRequest(`/admin/users/${userId}/limits`, {
    method: "PATCH",
    token,
    body: {
      maxActiveSessions,
      maxQueuedRequests,
    },
  });
}
