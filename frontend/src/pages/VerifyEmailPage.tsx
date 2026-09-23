import { MailCheck, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { verifyEmail } from "../api/authApi";
import { BrandMark } from "../components/BrandMark";
import { getApiErrorMessage } from "../utils/apiError";

function readTokenFromFragment(): string {
  return new URLSearchParams(window.location.hash.replace(/^#/, "")).get("token") ?? "";
}

type Status = "ready" | "submitting" | "success" | "error";

export function VerifyEmailPage() {
  // Token lives in the URL fragment (never sent to servers or in Referer);
  // capture it once, then scrub it from the address bar.
  const [token] = useState(readTokenFromFragment);
  const [status, setStatus] = useState<Status>("ready");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);

  // Verification is an explicit click, not automatic on load, so mail
  // scanners and link previewers that fetch the URL can't spend the token.
  async function handleConfirm(): Promise<void> {
    setStatus("submitting");
    try {
      const response = await verifyEmail(token);
      setMessage(response.message);
      setStatus("success");
    } catch (requestError) {
      setMessage(getApiErrorMessage(requestError, "Unable to verify your email."));
      setStatus("error");
    }
  }

  const invalid = !token || status === "error";

  return (
    <main className="auth-result-page">
      <section className="auth-result-card" role={invalid ? "alert" : "status"}>
        <div className="auth-result-brand"><span><BrandMark size={18} /></span>ScanHive</div>

        {status === "success" ? (
          <>
            <div className="auth-result-icon"><MailCheck size={25} /></div>
            <h1>Email verified</h1>
            <p>{message}</p>
            <Link className="primary-button" to="/login">Continue to sign in</Link>
          </>
        ) : invalid ? (
          <>
            <div className="auth-result-icon error"><ShieldAlert size={25} /></div>
            <h1>Verification link not valid</h1>
            <p>{message || "This verification link is invalid or incomplete."}</p>
            <Link className="primary-button" to="/resend-verification">Request a new link</Link>
          </>
        ) : (
          <>
            <div className="auth-result-icon"><MailCheck size={25} /></div>
            <h1>Confirm your email</h1>
            <p>Click below to verify your email address and finish creating your account.</p>
            <button
              type="button"
              className="primary-button"
              disabled={status === "submitting"}
              onClick={handleConfirm}
            >
              {status === "submitting" ? "Verifying..." : "Verify my email"}
            </button>
          </>
        )}
      </section>
    </main>
  );
}
