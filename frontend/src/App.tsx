import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { lazy, Suspense } from "react";

import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { AcceptInvitePage } from "./pages/AcceptInvitePage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import { ResendVerificationPage } from "./pages/ResendVerificationPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProjectDashboardPage } from "./pages/ProjectDashboardPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ScanFindingsPage } from "./pages/ScanFindingsPage";
import { FindingDetailsPage } from "./pages/FindingDetailsPage";
import { IamSettingsPage } from "./pages/IamSettingsPage";
import { RoleEditorPage } from "./pages/RoleEditorPage";
import { UserEditorPage } from "./pages/UserEditorPage";

const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })),
);

function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={<LoginPage />}
      />
      <Route
        path="/register"
        element={<RegisterPage />}
      />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/resend-verification" element={<ResendVerificationPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/accept-invite/:token" element={<AcceptInvitePage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route
            index
            element={
              <Navigate
                to="/projects"
                replace
              />
            }
          />

          <Route
            path="/dashboard"
            element={(
              <Suspense fallback={<div className="loading-state">Loading analytics...</div>}>
                <DashboardPage />
              </Suspense>
            )}
          />

          <Route
            path="/projects"
            element={<ProjectsPage />}
          />

          <Route
            path="/projects/:projectId"
            element={<ProjectDashboardPage />}
          />

          <Route
            path="/projects/:projectId/scans"
            element={<ProjectDashboardPage />}
          />

          <Route
            path="/projects/:projectId/settings"
            element={<ProjectDashboardPage />}
          />

          <Route
            path="/projects/:projectId/scans/:scanId/results"
            element={<ScanFindingsPage />}
          />

          <Route
            path="/projects/:projectId/scans/:scanId/results/:findingId"
            element={<FindingDetailsPage />}
          />

          <Route
            path="/settings/iam"
            element={<IamSettingsPage />}
          />

          <Route
            path="/settings"
            element={<Navigate to="/settings/iam" replace />}
          />

          <Route
            path="/settings/iam/roles/new"
            element={<RoleEditorPage />}
          />

          <Route
            path="/settings/iam/roles/:roleId/edit"
            element={<RoleEditorPage />}
          />

          <Route
            path="/settings/iam/users/:userId/edit"
            element={<UserEditorPage />}
          />

          <Route
            path="/settings/api-keys"
            element={<Navigate to="/settings/iam?section=api-keys" replace />}
          />
        </Route>
      </Route>

      <Route
        path="*"
        element={<NotFoundPage />}
      />
    </Routes>
  );
}

export default App;
