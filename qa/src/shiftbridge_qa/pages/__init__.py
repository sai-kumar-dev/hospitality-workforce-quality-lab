"""Focused Playwright page objects for ShiftBridge."""

from shiftbridge_qa.pages.applicant_list import ApplicantListPage
from shiftbridge_qa.pages.candidate_dashboard import CandidateDashboardPage
from shiftbridge_qa.pages.create_job import CreateJobPage
from shiftbridge_qa.pages.employer_dashboard import EmployerDashboardPage
from shiftbridge_qa.pages.job_detail import JobDetailPage
from shiftbridge_qa.pages.jobs import JobsPage
from shiftbridge_qa.pages.login import LoginPage
from shiftbridge_qa.pages.registration import RegistrationPage

__all__ = [
    "ApplicantListPage",
    "CandidateDashboardPage",
    "CreateJobPage",
    "EmployerDashboardPage",
    "JobDetailPage",
    "JobsPage",
    "LoginPage",
    "RegistrationPage",
]
