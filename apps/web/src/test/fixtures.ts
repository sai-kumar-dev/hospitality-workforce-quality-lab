import type { Job, PaginatedResponse, User } from "../types/domain";

export const candidate: User = {
  id: 11,
  email: "candidate@shiftbridge.test",
  full_name: "Casey Candidate",
  role: "candidate",
  created_at: "2026-01-02T09:00:00Z",
};

export const employer: User = {
  id: 21,
  email: "employer.a@shiftbridge.test",
  full_name: "Emery Employer",
  role: "employer",
  created_at: "2026-01-02T09:00:00Z",
};

export const frontDeskJob: Job = {
  id: 101,
  title: "Front Desk Supervisor",
  company_name: "Harbour House Hotel",
  location: "Dublin",
  employment_type: "full_time",
  description:
    "Lead a welcoming front desk team and help every guest begin their stay with confidence.",
  required_skills: ["Guest service", "Opera PMS", "Team leadership"],
  created_at: "2026-07-20T10:30:00Z",
  employer_id: employer.id,
  active: true,
};

export function pageOf<T>(items: T[]): PaginatedResponse<T> {
  return {
    items,
    page: 1,
    page_size: 8,
    total: items.length,
    total_pages: items.length ? 1 : 0,
  };
}

export function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type":
        status >= 400 ? "application/problem+json" : "application/json",
      "x-request-id": "test-request-123",
    },
  });
}

export function unauthorizedResponse(): Response {
  return jsonResponse(
    {
      code: "AUTHENTICATION_REQUIRED",
      title: "Authentication required",
      status: 401,
      detail: "Please sign in to continue.",
      request_id: "test-request-123",
    },
    401,
  );
}
