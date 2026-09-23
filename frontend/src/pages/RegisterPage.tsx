import {
  Building2,
  LockKeyhole,
  Mail,
  User,
} from "lucide-react";

import {
  type FormEvent,
  useState,
} from "react";

import {
  Link,
  Navigate,
} from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { getApiErrorMessage } from "../utils/apiError";
import { BrandLogo } from "../components/BrandMark";

export function RegisterPage() {
  const {
    register,
    isAuthenticated,
  } = useAuth();

  const [organizationName, setOrganizationName] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/projects" replace />;
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);

    try {
      const message = await register({
        organization_name: organizationName.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        password,
      });

      setNotice(message);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Unable to create your organization. Please try again."));
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
            Bring your team&apos;s security posture into one place.
          </h1>

          <p>
            Create your organization to start consolidating Trivy,
            Gitleaks, Semgrep, Snyk and other SARIF reports into one
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
            <h2>Create your organization</h2>
            <p>Register to get started with ScanHive.</p>
          </div>

          {error && (
            <div className="alert-error">
              {error}
            </div>
          )}

          {notice && (
            <div className="login-success" role="status">
              {notice}
              <p className="login-alt-action">
                <Link to="/resend-verification">Didn&apos;t get it? Resend the email</Link>
              </p>
            </div>
          )}

          <label className="form-group">
            <span>Organization name</span>

            <div className="input-with-icon">
              <Building2 size={18} />

              <input
                value={organizationName}
                onChange={(event) => setOrganizationName(event.target.value)}
                placeholder="Acme Corporation"
                autoComplete="organization"
                minLength={2}
                maxLength={150}
                required
              />
            </div>
          </label>

          <div className="register-name-row">
            <label className="form-group">
              <span>First name</span>

              <div className="input-with-icon">
                <User size={18} />

                <input
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  placeholder="Ada"
                  autoComplete="given-name"
                  maxLength={100}
                  required
                />
              </div>
            </label>

            <label className="form-group">
              <span>Last name</span>

              <div className="input-with-icon">
                <User size={18} />

                <input
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  placeholder="Lovelace"
                  autoComplete="family-name"
                  maxLength={100}
                />
              </div>
            </label>
          </div>

          <label className="form-group">
            <span>Email address</span>

            <div className="input-with-icon">
              <Mail size={18} />

              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
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
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
                autoComplete="new-password"
                minLength={8}
                required
                aria-describedby="password-hint"
              />
            </div>
            <small id="password-hint" className="password-hint">
              Use 8+ characters. Avoid common passwords and anything containing your email.
              A few unrelated words make a strong passphrase.
            </small>
          </label>

          <label className="form-group">
            <span>Confirm password</span>

            <div className="input-with-icon">
              <LockKeyhole size={18} />

              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Re-enter your password"
                autoComplete="new-password"
                minLength={8}
                required
              />
            </div>
          </label>

          <button
            type="submit"
            className="primary-button"
            disabled={isSubmitting || Boolean(notice)}
          >
            {isSubmitting
              ? "Creating organization..."
              : "Create organization"}
          </button>

          <p className="login-alt-action">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </form>
      </section>
    </div>
  );
}
