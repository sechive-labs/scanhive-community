import {
  LockKeyhole,
  Mail,
} from "lucide-react";

import {
  type FormEvent,
  useState,
} from "react";

import {
  Link,
  Navigate,
  useLocation,
  useNavigate,
} from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import axios from "axios";
import { getApiErrorMessage } from "../utils/apiError";
import { BrandLogo } from "../components/BrandMark";

interface LocationState {
  from?: string;
  passwordReset?: boolean;
}

export function LoginPage() {
  const {
    login,
    isAuthenticated,
  } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();

  const state =
    location.state as LocationState | null;

  const destination = state?.from || "/projects";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [needsVerification, setNeedsVerification] = useState(false);
  const [isSubmitting, setIsSubmitting] =
    useState(false);

  if (isAuthenticated) {
    return <Navigate to="/projects" replace />;
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    setError("");
    setNeedsVerification(false);
    setIsSubmitting(true);

    try {
      await login({
        email: email.trim(),
        password,
      });

      navigate(destination, {
        replace: true,
      });
    } catch (requestError) {
      const detail: unknown = axios.isAxiosError(requestError) ? requestError.response?.data?.detail : undefined;
      setNeedsVerification(
        typeof detail === "object" && detail !== null && "code" in detail && detail.code === "email_not_verified",
      );
      setError(getApiErrorMessage(requestError, "Unable to sign in. Check your credentials."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <section className="login-hero">
        <div className="login-hero-content">
          <div className="hero-logo">
            <BrandLogo size={132} />
          </div>

          <p className="eyebrow">
            Unified security visibility
          </p>

          <h1>
            Manage results from every security scanner.
          </h1>

          <p>
            Consolidate Trivy, Gitleaks, Semgrep,
            Snyk and other SARIF reports into one
            project-focused dashboard.
          </p>
        </div>
      </section>

      <section className="login-form-section">
        <form
          className="login-card"
          onSubmit={handleSubmit}
        >
          <div className="login-heading">
            <h2>Welcome back</h2>
            <p>Sign in to your ScanHive account.</p>
          </div>

          {state?.passwordReset && (
            <div className="login-success" role="status">
              Password reset. Sign in with your new password.
            </div>
          )}

          {error && (
            <div className="alert-error">
              {error}
              {needsVerification && (
                <>
                  {" "}
                  <Link to="/resend-verification">Resend verification email</Link>
                </>
              )}
            </div>
          )}

          <label className="form-group">
            <span>Email address</span>

            <div className="input-with-icon">
              <Mail size={18} />

              <input
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                placeholder="name@company.com"
                autoComplete="email"
                required
              />
            </div>
          </label>

          <label className="form-group">
            <span>Password</span>

            <div className="input-with-icon">
              <LockKeyhole size={18} />

              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />
            </div>
          </label>

          <p className="login-forgot-link">
            <Link to="/forgot-password">Forgot password?</Link>
          </p>

          <button
            type="submit"
            className="primary-button"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? "Signing in..."
              : "Sign in"}
          </button>

          <p className="login-alt-action">
            Don&apos;t have an organization yet? <Link to="/register">Create one</Link>
          </p>
        </form>
      </section>
    </div>
  );
}
