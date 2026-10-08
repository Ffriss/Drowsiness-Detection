export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function j(res) {
  if (!res.ok) {
    let msg = `${res.status}`;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export const getModels = () => fetch(`${API}/api/models`, { cache: "no-store" }).then(j);
export const getModel = (name) => fetch(`${API}/api/models/${name}`, { cache: "no-store" }).then(j);
export const getHistory = (limit = 200) => fetch(`${API}/api/history?limit=${limit}`, { cache: "no-store" }).then(j);
export const getStats = () => fetch(`${API}/api/stats`, { cache: "no-store" }).then(j);
export const clearHistory = () => fetch(`${API}/api/history`, { method: "DELETE" }).then(j);

export const getSettings = () => fetch(`${API}/api/settings`, { cache: "no-store" }).then(j);
export const saveSettings = (patch) =>
  fetch(`${API}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  }).then(j);
export const resetSettings = () => fetch(`${API}/api/settings/reset`, { method: "POST" }).then(j);

export function predictFrame(blob, model, sessionId) {
  const fd = new FormData();
  fd.append("file", blob, "frame.jpg");
  fd.append("model", model);
  fd.append("session_id", sessionId);
  return fetch(`${API}/api/predict`, { method: "POST", body: fd }).then(j);
}
