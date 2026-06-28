const API_BASE = "";
const AUTH_TOKEN_KEY = "career_caddy_token";
const AUTH_USER_KEY = "career_caddy_user";
const isLoginPage = location.pathname.endsWith("/login.html") || location.pathname === "/login";
if (!isLoginPage && !localStorage.getItem(AUTH_TOKEN_KEY)) location.replace("/login.html");
async function apiRequest(path, options = {}) {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const user = JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "null");
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (user?.user_id) headers.set("X-User-Id", user.user_id);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(API_BASE + path, { ...options, headers });
  if (response.status === 401 && !path.endsWith("/login")) {
    localStorage.removeItem(AUTH_TOKEN_KEY); localStorage.removeItem(AUTH_USER_KEY);
    if (!isLoginPage) location.replace("/login.html");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response;
}
const qs = (params) => new URLSearchParams(Object.entries(params || {}).filter(([,v]) => v !== "" && v !== null && v !== undefined)).toString();
const CareerAPI = {
  login: (username, password) => apiRequest("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  getCurrentUser: () => apiRequest("/api/auth/me"),
  logout: () => apiRequest("/api/auth/logout", { method: "POST" }),
  getStats: () => apiRequest("/api/dashboard/stats"),
  getJobs: (filters = {}) => apiRequest(`/api/jobs?${qs(filters)}`),
  runAgent: (jobId) => apiRequest(`/api/agent/run/${jobId}`, { method: "POST", headers: {"Accept": "text/event-stream"} }),
  importJob: (job) => apiRequest("/api/jobs/import", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(job) }),
  extractJobFromUrl: (url) => apiRequest("/api/jobs/extract", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ url }) }),
  extractJobFromText: (jobText, applyUrl) => apiRequest("/api/jobs/extract-text", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ job_text: jobText, apply_url: applyUrl || null }) }),
  scoreJob: (jobId) => apiRequest(`/api/jobs/${jobId}/score`, { method: "POST" }),
  markReady: (jobId) => apiRequest(`/api/jobs/${jobId}/ready`, { method: "POST" }),
  skipJob: (jobId) => apiRequest(`/api/jobs/${jobId}/skip`, { method: "POST" }),
  deleteJob: (jobId) => apiRequest(`/api/jobs/${jobId}`, { method: "DELETE" }),
  prepareApplication: (jobId) => apiRequest(`/api/applications/${jobId}/prepare`, { method: "POST" }),
  getApplications: (filters = {}) => apiRequest(`/api/applications?${qs(filters)}`),
  getApplication: (applicationId) => apiRequest(`/api/applications/${applicationId}`),
  getAutomationStatus: (applicationId) => apiRequest(`/api/applications/${applicationId}/automation-status`),
  getApplicationScreenshot: (applicationId) => apiRequest(`/api/applications/${applicationId}/screenshot`),
  markSubmitted: (applicationId) => apiRequest(`/api/applications/${applicationId}/mark-submitted`, { method: "POST" }),
  saveApplicationReview: (applicationId, generatedAnswers, notes = "") => apiRequest(`/api/applications/${applicationId}/review`, { method: "PATCH", body: JSON.stringify({ generated_answers: generatedAnswers, notes }) }),
  regenerateAnswers: (applicationId) => apiRequest(`/api/applications/${applicationId}/regenerate-answers`, { method: "POST" }),
  startAutomation: (applicationId, confirmMissing = false) => apiRequest(`/api/applications/${applicationId}/start-automation`, { method: "POST", body: JSON.stringify({ confirm_missing: confirmMissing }) }),
  skipApplication: (applicationId) => apiRequest(`/api/applications/${applicationId}/skip`, { method: "POST" }),
  markBlocked: (applicationId, blocker) => apiRequest(`/api/applications/${applicationId}/mark-blocked`, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(blocker) }),
  uploadResume: (file, resumeType) => { const form = new FormData(); form.append("file", file); form.append("resume_type", resumeType); return apiRequest("/api/resumes/upload", { method: "POST", body: form }); },
  getResumes: () => apiRequest("/api/resumes"),
  parseResume: (resumeId) => apiRequest(`/api/resumes/${resumeId}/parse`, { method: "POST" }),
  setDefaultResume: (resumeId) => apiRequest(`/api/resumes/${resumeId}/set-default`, { method: "POST" }),
  deleteResume: (resumeId) => apiRequest(`/api/resumes/${resumeId}`, { method: "DELETE" }),
  getProfile: () => apiRequest("/api/profile"),
  saveProfile: (profile) => apiRequest("/api/profile", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(profile) }),
  exportExcel: async () => { const response = await apiRequest("/api/export/excel"); const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "careercaddy_export.xlsx"; link.click(); URL.revokeObjectURL(url); },
  initDb: () => apiRequest("/api/init-db", { method: "POST" })
};
window.CareerAPI = CareerAPI;
