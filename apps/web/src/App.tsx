import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { ApplicantsPage } from "./pages/ApplicantsPage";
import { CandidateDashboardPage } from "./pages/CandidateDashboardPage";
import { CreateJobPage } from "./pages/CreateJobPage";
import { DashboardRedirect } from "./pages/DashboardRedirect";
import { EmployerDashboardPage } from "./pages/EmployerDashboardPage";
import { HomePage } from "./pages/HomePage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsPage } from "./pages/JobsPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:jobId" element={<JobDetailPage />} />
        <Route path="dashboard" element={<DashboardRedirect />} />

        <Route element={<ProtectedRoute role="candidate" />}>
          <Route path="candidate" element={<CandidateDashboardPage />} />
          <Route
            path="candidate/dashboard"
            element={<CandidateDashboardPage />}
          />
          <Route path="applications" element={<CandidateDashboardPage />} />
        </Route>

        <Route element={<ProtectedRoute role="employer" />}>
          <Route path="employer" element={<EmployerDashboardPage />} />
          <Route
            path="employer/dashboard"
            element={<EmployerDashboardPage />}
          />
          <Route path="employer/jobs/new" element={<CreateJobPage />} />
          <Route
            path="employer/jobs/:jobId/applicants"
            element={<ApplicantsPage />}
          />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
