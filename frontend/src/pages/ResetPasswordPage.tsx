import { LockKeyhole } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { resetPassword } from "../api/authApi";
import { BrandLogo } from "../components/BrandMark";
import { getApiErrorMessage } from "../utils/apiError";

function readTokenFromFragment(): string {
  return new URLSearchParams(window.location.hash.replace(/^#/, "")).get("token") ?? "";
}

export function ResetPasswordPage() {
  const navigate = useNavigate();
  // The token travels in the URL fragment so it is never sent to a server or
  // leaked via Referer. Capture it once, then scrub it from the address bar
  // and browser history.
  const [token] = useState(readTokenFromFragment);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await resetPassword(token, password);
      navigate("/login", { replace: true, state: { passwordReset: true } });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Unable to reset your password."));
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
          <p className="eyebrow">Account recovery</p>
          <h1>Choose a new password.</h1>
          <p>You&apos;ll be signed out everywhere and asked to sign in again.</p>
        </div>
      </section>

      <section className="login-form-section">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-heading">
            <h2>New password</h2>
          </div>

          {!token ? (
            <>
              <div className="alert-error" role="alert">
                This password reset link is invalid or incomplete.
              </div>
              <Link className="primary-button" to="/forgot-password">Request a new link</Link>
            </>
          ) : (
            <>
              {error && <div className="alert-error">{error}</div>}

              <label className="form-group">
                <span>New password</span>
                <div className="input-with-icon">
                  <LockKeyhole size={18} />
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="At least 8 characters"
                    autoComplete="new-password"
                    minLength={8}
                    maxLength={128}
                    required
                  />
                </div>
              </label>

              <label className="form-group">
                <span>Confirm new password</span>
                <div className="input-with-icon">
                  <LockKeyhole size={18} />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Re-enter your password"
                    autoComplete="new-password"
                    minLength={8}
                    maxLength={128}
                    required
                  />
                </div>
              </label>

              <button type="submit" className="primary-button" disabled={isSubmitting}>
                {isSubmitting ? "Saving..." : "Reset password"}
              </button>

              <p className="login-alt-action">
                <Link to="/forgot-password">Request a new link</Link>
              </p>
            </>
          )}
        </form>
      </section>
    </div>
  );
}
