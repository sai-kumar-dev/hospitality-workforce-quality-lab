export type Role = "candidate" | "employer";
export type EntityId = number;

export interface User {
  id: EntityId;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
}

export interface Job {
  id: EntityId;
  title: string;
  company_name: string;
  location: string;
  employment_type: string;
  description: string;
  required_skills: string[];
  created_at: string;
  employer_id: EntityId;
  active: boolean;
}

export type ApplicationStatus =
  "submitted" | "reviewing" | "shortlisted" | "rejected" | "withdrawn";

export interface JobApplication {
  id: EntityId;
  job_id: EntityId;
  candidate_id: EntityId;
  cover_note: string;
  status: ApplicationStatus;
  applied_at: string;
  job?: Job;
}

export interface ApplicantApplication extends JobApplication {
  candidate: User;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface FieldError {
  field: string;
  message: string;
  type?: string;
}

export interface ProblemDetails {
  code: string;
  title: string;
  status: number;
  detail: string;
  request_id?: string;
  field_errors?: FieldError[];
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface CandidateRegistrationInput extends LoginInput {
  full_name: string;
}

export interface CreateJobInput {
  title: string;
  company_name: string;
  location: string;
  employment_type: string;
  description: string;
  required_skills: string[];
  active: boolean;
}

export interface JobFilters {
  keyword?: string;
  location?: string;
  page?: number;
  page_size?: number;
}
