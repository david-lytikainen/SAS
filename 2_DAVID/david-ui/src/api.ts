export type User = { name: string; email: string; role: string };
export type AuthResponse = { token: string; user: User };
export type PortfolioSite = { id: number; siteUrl: string; screenshotUrl: string; displayOrder: number };
export type RequestComment = { id: number; authorRole: string; body: string; createdAt: string; updatedAt: string };
export type WebsiteRequest = { requestNumber: string; customerName: string; customerEmail: string; customerPhone: string; projectDescription: string; targetDate: string; budgetRange: string; status: string; createdAt: string; updatedAt: string; viewerIsAdmin: boolean; comments: RequestComment[] };
export type RequestDraft = { customerName: string; customerEmail: string; customerPhone: string; projectDescription: string; targetDate: string; budgetRange: string };

const apiBaseUrl = process.env.REACT_APP_API_BASE_URL ?? "http://localhost:8002";

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "Request failed.");
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export const authApi = { login: (email: string, password: string) => request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }), validate: (token: string) => request<User>("/auth/validate-token", {}, token) };
export const portfolioApi = {
  list: () => request<PortfolioSite[]>("/portfolio"),
  listAdmin: (token: string) => request<PortfolioSite[]>("/admin/portfolio", {}, token),
  create: (token: string, siteUrl: string, screenshot: File) => { const body = new FormData(); body.append("site_url", siteUrl); body.append("screenshot", screenshot); return request<PortfolioSite>("/admin/portfolio", { method: "POST", body }, token); },
  update: (token: string, id: number, siteUrl: string, screenshot?: File) => { const body = new FormData(); body.append("site_url", siteUrl); if (screenshot) body.append("screenshot", screenshot); return request<PortfolioSite>(`/admin/portfolio/${id}`, { method: "PATCH", body }, token); },
  remove: (token: string, id: number) => request<{ status: string }>(`/admin/portfolio/${id}`, { method: "DELETE" }, token),
  reorder: (token: string, orderedIds: number[]) => request<{ status: string }>("/admin/portfolio/reorder", { method: "POST", body: JSON.stringify({ orderedIds }) }, token),
};
export const requestApi = {
  create: (draft: RequestDraft) => request<WebsiteRequest>("/requests", { method: "POST", body: JSON.stringify(draft) }),
  get: (number: string, token?: string) => request<WebsiteRequest>(`/requests/${number}`, {}, token),
  comment: (number: string, body: string, token?: string) => request<RequestComment>(`/requests/${number}/comments`, { method: "POST", body: JSON.stringify({ body }) }, token),
  listAdmin: (token: string) => request<WebsiteRequest[]>("/admin/requests", {}, token),
  status: (token: string, number: string, status: string) => request<WebsiteRequest>(`/admin/requests/${number}/status`, { method: "POST", body: JSON.stringify({ status }) }, token),
};
