export type ApiErrorDetail = {
  code: string;
  message: string;
  fields?: Record<string, string>;
  existing?: Record<string, unknown> | null;
  [key: string]: unknown;
};

export class ApiError extends Error {
  status: number;
  detail: ApiErrorDetail;

  constructor(status: number, detail: ApiErrorDetail) {
    super(detail.message);
    this.status = status;
    this.detail = detail;
  }

  get code() {
    return this.detail.code;
  }

  get fields() {
    return this.detail.fields ?? {};
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

function withQuery(path: string, query?: Query) {
  if (!query) return path;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `${path}?${s}` : path;
}

async function request<T>(method: string, path: string, body?: unknown, query?: Query): Promise<T> {
  let res: Response;
  try {
    res = await fetch(withQuery(`/api${path}`, query), {
      method,
      credentials: "same-origin",
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch {
    // И7: нет связи с сервером – данные формы остаются на месте, запись не создаётся.
    throw new ApiError(0, { code: "NETWORK", message: "Нет связи с сервером. Данные не сохранены, повторите попытку." });
  }
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail: ApiErrorDetail =
      data && typeof data.detail === "object" && data.detail
        ? data.detail
        : { code: "HTTP_" + res.status, message: (data && data.detail) || `Ошибка сервера (${res.status})` };
    if (res.status === 401 && typeof window !== "undefined" && !location.pathname.startsWith("/login")) {
      location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search);
    }
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>("GET", path, undefined, query),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body ?? {}),
};

export function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Неизвестная ошибка";
}
