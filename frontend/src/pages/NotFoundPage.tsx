import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="not-found-page">
      <p className="eyebrow">404</p>

      <h1>Page not found</h1>

      <p>
        The page you requested does not exist.
      </p>

      <Link
        to="/projects"
        className="primary-button link-button"
      >
        Return to projects
      </Link>
    </div>
  );
}