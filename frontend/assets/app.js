function renderStatusBadge(status) {
  const map = {
    FOUND: "bg-gray-100 text-gray-700 border-gray-200", SCORED: "bg-purple-100 text-purple-700 border-purple-200",
    READY_TO_APPLY: "bg-blue-100 text-blue-700 border-blue-200", IN_PROGRESS: "bg-sky-100 text-sky-700 border-sky-200",
    NEEDS_REVIEW: "bg-amber-100 text-amber-800 border-amber-200", SUBMITTED: "bg-emerald-100 text-emerald-700 border-emerald-200",
    SKIPPED: "bg-slate-100 text-slate-700 border-slate-200", FAILED: "bg-red-100 text-red-700 border-red-200",
    NEEDS_LOGIN: "bg-orange-100 text-orange-800 border-orange-200", NEEDS_CAPTCHA: "bg-orange-100 text-orange-800 border-orange-200",
    DUPLICATE: "bg-zinc-100 text-zinc-700 border-zinc-200"
  };
  return `<span class="status-badge ${map[status] || map.FOUND}">${status || "UNKNOWN"}</span>`;
}
function formatDate(date) {
  if (!date) return "";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(date));
}
function showToast(message, type = "info") {
  const root = document.getElementById("toast-root");
  if (!root) return;
  const color = type === "error" ? "border-error text-on-error-container bg-error-container" : "border-outline-variant text-on-surface bg-surface-container-lowest";
  const el = document.createElement("div");
  el.className = `border ${color} rounded-lg px-4 py-3 shadow-lg max-w-sm`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}
function handleError(error) {
  console.error(error);
  showToast(error.message || "Something went wrong", "error");
}
function initializeSidebarActiveState() {
  const active = document.querySelector("main")?.dataset.activeNav;
  document.querySelectorAll(`[data-nav="${active}"]`).forEach((a) => a.classList.add("active"));
}
function bindImportButtons() {
  document.querySelectorAll("[data-open-import]").forEach((button) => button.addEventListener("click", () => {
    window.location.href = "/jobs.html#import";
  }));
}
document.addEventListener("DOMContentLoaded", () => { initializeSidebarActiveState(); bindImportButtons(); });
window.renderStatusBadge = renderStatusBadge;
window.formatDate = formatDate;
window.showToast = showToast;
window.handleError = handleError;
