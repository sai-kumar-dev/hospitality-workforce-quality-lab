import type {
  ApplicantApplication,
  CandidateRegistrationInput,
  CreateJobInput,
  FieldError,
  Job,
  JobApplication,
  JobFilters,
  LoginInput,
  PaginatedResponse,
  ProblemDetails,
  User,
} from "../types/domain";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(
  /\/+$/,
  "",
);
const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 10_000);
const API_TIMEOUT_MS =
  Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : 10_000;

type RequestOptions = Omit<RequestInit, "body" | "credentials"> & {
  body?: unknown;
  timeoutMs?: number;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly title: string;
  readonly detail: string;
  readonly requestId?: string;
  readonly fieldErrors: FieldError[];

  constructor(problem: ProblemDetails) {
    super(problem.detail);
    this.name = "ApiError";
    this.status = problem.status;
    this.code = problem.code;
    this.title = problem.title;
    this.detail = problem.detail;
    this.requestId = problem.request_id;
    this.fieldErrors = problem.field_errors ?? [];
  }
}

export class ApiNetworkError extends Error {
  readonly code: "NETWORK_TIMEOUT" | "NETWORK_UNREACHABLE";

  constructor(
    code: "NETWORK_TIMEOUT" | "NETWORK_UNREACHABLE",
    message: string,
  ) {
    super(message);
    this.name = "ApiNetworkError";
    this.code = code;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function parseFieldErrors(value: unknown): FieldError[] {
  if (!Array.isArray(value)) return [];

  return value.flatMap((item) => {
    if (!isRecord(item)) return [];
    const field = asString(item.field, "");
    const message = asString(item.message, "");
    if (!field || !message) return [];
    const type = typeof item.type === "string" ? item.type : undefined;
    return [{ field, message, ...(type ? { type } : {}) }];
  });
}

export function parseProblemDetails(
  payload: unknown,
  status: number,
  requestIdHeader?: string | null,
): ProblemDetails {
  if (!isRecord(payload)) {
    return {
      code: "HTTP_ERROR",
      title: "Request failed",
      status,
      detail: "The service returned an unexpected response.",
      ...(requestIdHeader ? { request_id: requestIdHeader } : {}),
    };
  }

  const requestId =
    asString(payload.request_id, "") || requestIdHeader || undefined;

  return {
    code: asString(payload.code, "HTTP_ERROR"),
    title: asString(payload.title, "Request failed"),
    status: asNumber(payload.status, status),
    detail: asString(
      payload.detail,
      "The service could not complete the request.",
    ),
    ...(requestId ? { request_id: requestId } : {}),
    field_errors: parseFieldErrors(payload.field_errors),
  };
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? API_TIMEOUT_MS;
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  if (options.signal) {
    if (options.signal.aborted) controller.abort();
    options.signal.addEventListener("abort", () => controller.abort(), {
      once: true,
    });
  }

  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body !== undefined)
    headers.set("Content-Type", "application/json");

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: "include",
      headers,
      signal: controller.signal,
    });

    if (response.status === 204) return undefined as T;

    const contentType = response.headers.get("content-type") ?? "";
    const payload: unknown = contentType.includes("json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      throw new ApiError(
        parseProblemDetails(
          payload,
          response.status,
          response.headers.get("x-request-id"),
        ),
      );
    }

    return payload as T;
  } catch (error: unknown) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted && !(options.signal?.aborted ?? false)) {
      throw new ApiNetworkError(
        "NETWORK_TIMEOUT",
        "The request timed out. Please try again.",
      );
    }
    if (options.signal?.aborted) throw error;
    throw new ApiNetworkError(
      "NETWORK_UNREACHABLE",
      "ShiftBridge cannot reach the service. Check your connection and try again.",
    );
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function unwrapUser(payload: User | { user: User }): User {
  return "user" in payload ? payload.user : payload;
}

function queryString(filters: JobFilters): string {
  const params = new URLSearchParams();
  if (filters.keyword?.trim()) params.set("keyword", filters.keyword.trim());
  if (filters.location?.trim()) params.set("location", filters.location.trim());
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function messageForError(error: unknown): string {
  if (error instanceof ApiError) return error.detail;
  if (error instanceof ApiNetworkError) return error.message;
  return "Something unexpected happened. Please try again.";
}

export function fieldErrorsFor(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {};
  return Object.fromEntries(
    error.fieldErrors.map(({ field, message }) => [field, message]),
  );
}

export const api = {
  async register(input: CandidateRegistrationInput): Promise<User> {
    const payload = await request<User | { user: User }>("/auth/register", {
      method: "POST",
      body: input,
    });
    return unwrapUser(payload);
  },

  async login(input: LoginInput): Promise<User> {
    const payload = await request<User | { user: User }>("/auth/login", {
      method: "POST",
      body: input,
    });
    return unwrapUser(payload);
  },

  logout(): Promise<void> {
    return request<void>("/auth/logout", { method: "POST" });
  },

  me(options?: Pick<RequestOptions, "signal">): Promise<User> {
    return request<User>("/auth/me", options);
  },

  jobs(filters: JobFilters = {}): Promise<PaginatedResponse<Job>> {
    return request<PaginatedResponse<Job>>(`/jobs${queryString(filters)}`);
  },

  job(jobId: number, options?: Pick<RequestOptions, "signal">): Promise<Job> {
    return request<Job>(`/jobs/${jobId}`, options);
  },

  createJob(input: CreateJobInput): Promise<Job> {
    return request<Job>("/jobs", { method: "POST", body: input });
  },

  employerJobs(
    filters: Pick<JobFilters, "page" | "page_size"> = {},
  ): Promise<PaginatedResponse<Job>> {
    return request<PaginatedResponse<Job>>(
      `/employer/jobs${queryString(filters)}`,
    );
  },

  apply(jobId: number, coverNote: string): Promise<JobApplication> {
    return request<JobApplication>(`/jobs/${jobId}/applications`, {
      method: "POST",
      body: { cover_note: coverNote },
    });
  },

  myApplications(
    filters: Pick<JobFilters, "page" | "page_size"> = {},
  ): Promise<PaginatedResponse<JobApplication>> {
    return request<PaginatedResponse<JobApplication>>(
      `/applications/me${queryString(filters)}`,
    );
  },

  applicants(
    jobId: number,
    filters: Pick<JobFilters, "page" | "page_size"> = {},
  ): Promise<PaginatedResponse<ApplicantApplication>> {
    return request<PaginatedResponse<ApplicantApplication>>(
      `/jobs/${jobId}/applicants${queryString(filters)}`,
    );
  },
};
