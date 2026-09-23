import { Mail } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { forgotPassword } from "../api/authApi";
import { BrandLogo } from "../components/BrandMark";
import { getApiErrorMessage } from "../utils/apiError";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await forgotPassword(email.trim());
      setMessage(response.message);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Unable to process your request. Please try again."));
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
          <h1>Forgot your password?</h1>
          <p>Enter your email and we&apos;ll send you a link to choose a new one.</p>
        </div>
      </section>

      <section className="login-form-section">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-heading">
            <h2>Reset password</h2>
            <p>The link expires shortly and works once.</p>
          </div>

          {error && <div className="alert-error">{error}</div>}
          {message && <div className="login-success" role="status">{message}</div>}

          {!message && (
            <>
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

              <button type="submit" className="primary-button" disabled={isSubmitting}>
                {isSubmitting ? "Sending..." : "Send reset link"}
              </button>
            </>
          )}

          <p className="login-alt-action">
            <Link to="/login">Back to sign in</Link>
          </p>
        </form>
      </section>
    </div>
  );
}
