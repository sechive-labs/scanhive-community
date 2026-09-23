import { LockKeyhole, ShieldAlert, User } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { acceptInvitation, getInvitationPreview } from "../api/authApi";
import { useAuth } from "../auth/AuthContext";
import { BrandMark } from "../components/BrandMark";
import { LoadingState } from "../components/LoadingState";
import { getApiErrorMessage } from "../utils/apiError";

export function AcceptInvitePage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { authenticate, isAuthenticated } = useAuth();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const previewQuery = useQuery({
    queryKey: ["invitation-preview", token],
    queryFn: () => getInvitationPreview(token as string),
    enabled: Boolean(token),
    retry: false,
  });

  if (isAuthenticated) {
    return <Navigate to="/projects" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) return;

    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await acceptInvitation(token, {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        password,
      });
      authenticate(response.access_token);
      navigate("/projects", { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Unable to accept this invitation."));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (previewQuery.isLoading) {
    return (
      <main className="auth-result-page">
        <section className="auth-result-card processing">
          <div className="auth-result-brand"><span><BrandMark size={18} /></span>ScanHive</div>
          <LoadingState size={22}>Loading invitation...</LoadingState>
        </section>
      </main>
    );
  }

  if (previewQuery.isError || !previewQuery.data) {
    return (
      <main className="auth-result-page">
        <section className="auth-result-card" role="alert">
          <div className="auth-result-brand"><span><BrandMark size={18} /></span>ScanHive</div>
          <div className="auth-result-icon error"><ShieldAlert size={25} /></div>
          <h1>Invitation not found</h1>
          <p>This invitation link is invalid, has expired, or has already been used.</p>
          <Link className="primary-button" to="/login">Return to sign in</Link>
        </section>
      </main>
    );
  }

  const preview = previewQuery.data;

  return (
    <div className="login-page">
      <section className="login-hero">
        <div className="login-hero-content">
          <div className="hero-logo">
            <BrandMark size={64} />
          </div>
          <p className="eyebrow">You&apos;re invited</p>
          <h1>Join {preview.organization_name} on ScanHive.</h1>
          <p>Set your name and password to finish creating your account.</p>
        </div>
      </section>

      <section className="login-form-section">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-heading">
            <h2>Accept invitation</h2>
            <p>{preview.email}</p>
          </div>

          {error && <div className="alert-error">{error}</div>}

          <div className="register-name-row">
            <label className="form-group">
              <span>First name</span>
              <div className="input-with-icon">
                <User size={18} />
                <input value={firstName} onChange={(event) => setFirstName(event.target.value)} maxLength={100} required />
              </div>
            </label>
            <label className="form-group">
              <span>Last name</span>
              <div className="input-with-icon">
                <User size={18} />
                <input value={lastName} onChange={(event) => setLastName(event.target.value)} maxLength={100} />
              </div>
            </label>
          </div>

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
              />
            </div>
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

          <button type="submit" className="primary-button" disabled={isSubmitting}>
            {isSubmitting ? "Joining..." : "Accept invitation"}
          </button>
        </form>
      </section>
    </div>
  );
}
