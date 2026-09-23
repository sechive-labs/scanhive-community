import { Mail } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { resendVerification } from "../api/authApi";
import { BrandLogo } from "../components/BrandMark";
import { getApiErrorMessage } from "../utils/apiError";

export function ResendVerificationPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const response = await resendVerification(email.trim());
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
          <p className="eyebrow">Verify your email</p>
          <h1>Need a new verification link?</h1>
          <p>Enter the email you signed up with and we&apos;ll send a fresh link.</p>
        </div>
      </section>

      <section className="login-form-section">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-heading">
            <h2>Resend verification</h2>
            <p>Older links stop working once a new one is sent.</p>
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
                {isSubmitting ? "Sending..." : "Send verification link"}
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
