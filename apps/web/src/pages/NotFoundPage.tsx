import { Link } from "react-router-dom";
import { PageTitle } from "../components/PageTitle";

export function NotFoundPage() {
  return (
    <section className="not-found-page">
      <PageTitle title="Page not found" />
      <div className="container not-found-page__inner">
        <div className="not-found-page__code" aria-hidden="true">
          404
        </div>
        <p className="eyebrow">Looks like this shift moved</p>
        <h1>Page not found</h1>
        <p className="lead">
          The page you were looking for is not here. The opportunity you want
          may still be waiting in job search.
        </p>
        <div className="hero__actions">
          <Link className="button" to="/jobs">
            Browse open roles
          </Link>
          <Link className="button button--secondary" to="/">
            Go to homepage
          </Link>
        </div>
      </div>
    </section>
  );
}
