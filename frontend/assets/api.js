const API_BASE = "";
async function apiRequest(path, options = {}) {
  const response = await fetch(API_BASE + path, options);
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
  getStats: () => apiRequest("/api/dashboard/stats"),
  getJobs: (filters = {}) => apiRequest(`/api/jobs?${qs(filters)}`),
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
  markSubmitted: (applicationId) => apiRequest(`/api/applications/${applicationId}/mark-submitted`, { method: "POST" }),
  saveApplicationReview: (applicationId, generatedAnswers, notes = "") => apiRequest(`/api/applications/${applicationId}/review`, { method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ generated_answers: generatedAnswers, notes }) }),
  startAutomation: (applicationId) => apiRequest(`/api/applications/${applicationId}/start-automation`, { method: "POST" }),
  skipApplication: (applicationId) => apiRequest(`/api/applications/${applicationId}/skip`, { method: "POST" }),
  markBlocked: (applicationId, blocker) => apiRequest(`/api/applications/${applicationId}/mark-blocked`, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(blocker) }),
  uploadResume: (file, resumeType) => { const form = new FormData(); form.append("file", file); form.append("resume_type", resumeType); return apiRequest("/api/resumes/upload", { method: "POST", body: form }); },
  getResumes: () => apiRequest("/api/resumes"),
  deleteResume: (resumeId) => apiRequest(`/api/resumes/${resumeId}`, { method: "DELETE" }),
  getProfile: () => apiRequest("/api/profile"),
  saveProfile: (profile) => apiRequest("/api/profile", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(profile) }),
  exportExcel: () => { window.location.href = "/api/export/excel"; },
  initDb: () => apiRequest("/api/init-db", { method: "POST" })
};
window.CareerAPI = CareerAPI;
