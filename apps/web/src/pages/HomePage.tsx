import { Link } from "react-router-dom";
import { PageTitle } from "../components/PageTitle";

export function HomePage() {
  return (
    <>
      <PageTitle title="Hospitality careers with momentum" />
      <section className="hero">
        <div className="container hero__grid">
          <div className="hero__content">
            <p className="eyebrow">
              Hospitality talent, thoughtfully connected
            </p>
            <h1>ShiftBridge Quality Engineering Lab</h1>
            <p className="hero__lead">
              Find hospitality work where your craft is valued—or build the team
              that keeps every guest experience moving.
            </p>
            <div className="hero__actions">
              <Link className="button button--large" to="/jobs">
                Explore open roles
              </Link>
              <Link
                className="button button--large button--secondary"
                to="/login"
              >
                Employer sign in
              </Link>
            </div>
            <ul className="hero__proof" aria-label="Marketplace benefits">
              <li>Verified local employers</li>
              <li>Clear role details</li>
              <li>Simple applications</li>
            </ul>
          </div>

          <aside className="opportunity-card" aria-label="Featured opportunity">
            <div className="opportunity-card__header">
              <span className="live-dot" aria-hidden="true" />
              New this week
            </div>
            <p className="opportunity-card__kicker">
              Featured hospitality role
            </p>
            <h2>Guest Experience Manager</h2>
            <p>The Harbour House · Dublin</p>
            <dl className="opportunity-card__facts">
              <div>
                <dt>Schedule</dt>
                <dd>Full time</dd>
              </div>
              <div>
                <dt>Focus</dt>
                <dd>Front office</dd>
              </div>
              <div>
                <dt>Team</dt>
                <dd>24 people</dd>
              </div>
            </dl>
            <Link className="text-link text-link--light" to="/jobs">
              See matching roles <span aria-hidden="true">→</span>
            </Link>
          </aside>
        </div>
      </section>

      <section className="value-section" aria-labelledby="built-for-heading">
        <div className="container">
          <p className="eyebrow">One marketplace, two ambitions</p>
          <h2 id="built-for-heading">
            Built for people who make hospitality happen
          </h2>
          <div className="value-grid">
            <article>
              <span className="number-mark" aria-hidden="true">
                01
              </span>
              <h3>Discover the right fit</h3>
              <p>
                Search by craft and location, then review the details that
                matter before you apply.
              </p>
            </article>
            <article>
              <span className="number-mark" aria-hidden="true">
                02
              </span>
              <h3>Apply with confidence</h3>
              <p>
                Share a focused note and track every submitted application from
                one calm dashboard.
              </p>
            </article>
            <article>
              <span className="number-mark" aria-hidden="true">
                03
              </span>
              <h3>Hire with clarity</h3>
              <p>
                Publish roles quickly and keep each applicant list connected to
                the right vacancy.
              </p>
            </article>
          </div>
        </div>
      </section>
    </>
  );
}
