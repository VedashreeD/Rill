import type {
  AlertRecord,
  AlertSettings,
  AuthResponse,
  MlStatus,
  ReportItem,
  UserMe,
  WorldLocation,
} from "../types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:4000";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("rill_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface ApiErrorBody {
  detail?: string;
  error?: string;
}

async function handle<T>(res: Response): Promise<T> {
  const data = (await res.json().catch(() => ({}))) as ApiErrorBody & T;
  if (!res.ok) {
    // FastAPI's default error shape is { detail: string }.
    const message = (data as ApiErrorBody).detail || (data as ApiErrorBody).error || "request failed";
    throw new Error(message);
  }
  return data as T;
}

export interface ListReportsParams {
  segmentCode?: string;
  minTier?: string;
}

export const api = {
  register: (username: string, password: string): Promise<AuthResponse> =>
    fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }).then((r) => handle<AuthResponse>(r)),

  login: (username: string, password: string): Promise<AuthResponse> =>
    fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }).then((r) => handle<AuthResponse>(r)),

  createReport: (formData: FormData): Promise<ReportItem> =>
    fetch(`${API_BASE}/api/reports`, {
      method: "POST",
      headers: { ...authHeaders() },
      body: formData,
    }).then((r) => handle<ReportItem>(r)),

  listReports: (params: ListReportsParams): Promise<ReportItem[]> => {
    const qs = new URLSearchParams();
    if (params.segmentCode) qs.set("segmentCode", params.segmentCode);
    if (params.minTier) qs.set("minTier", params.minTier);

    return fetch(`${API_BASE}/api/reports?${qs.toString()}`, {
      headers: { ...authHeaders() },
    }).then((r) => handle<ReportItem[]>(r));
  },

  tagReportCondition: (reportId: string, tag: string): Promise<ReportItem> =>
    fetch(`${API_BASE}/api/reports/${reportId}/tag`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ tag }),
    }).then((r) => handle<ReportItem>(r)),

  listLocations: (): Promise<WorldLocation[]> =>
    fetch(`${API_BASE}/api/locations`).then((r) => handle<WorldLocation[]>(r)),

  me: (): Promise<UserMe> =>
    fetch(`${API_BASE}/api/users/me`, { headers: { ...authHeaders() } }).then((r) =>
      handle<UserMe>(r)
    ),

  updateAlertSettings: (settings: AlertSettings): Promise<AlertSettings> =>
    fetch(`${API_BASE}/api/users/me/alert-settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(settings),
    }).then((r) => handle<AlertSettings>(r)),

  listMyAlerts: (): Promise<AlertRecord[]> =>
    fetch(`${API_BASE}/api/users/me/alerts`, { headers: { ...authHeaders() } }).then((r) =>
      handle<AlertRecord[]>(r)
    ),

  getMlStatus: (): Promise<MlStatus> =>
    fetch(`${API_BASE}/api/ml/status`).then((r) => handle<MlStatus>(r)),
};
