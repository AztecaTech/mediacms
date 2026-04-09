import React from 'react';
import { LmsOrgAtRiskPanel } from '../components/learning/LmsOrgAtRiskPanel';
import { LmsOrgLdapSourcesPanel } from '../components/learning/LmsOrgLdapSourcesPanel';
import { LmsOrgTrendChartsPanel } from '../components/learning/LmsOrgTrendChartsPanel';
import { Page } from './Page';

import './OrgManagerLearningPage.scss';

export function OrgManagerLearningPage({ id = 'lms_org_learning' }) {
  return (
    <Page id={id}>
      <div className="lms-page lms-org-learning lms-shell lms-shell--wide">
        <h1 className="page-title">Org learning</h1>
        <p className="lms-intro">
          Monitor engagement trends, identify learners who may need support, and manage directory connections for your
          organization—all in one place.
        </p>
        <div className="lms-hint-box">
          Need the public catalog or your own courses? Use the links at the bottom of this page.
        </div>

        <section className="lms-section" aria-labelledby="lms-org-trends-heading">
          <h2 id="lms-org-trends-heading" className="lms-section__title">
            Trends
          </h2>
          <p className="lms-help-text" style={{ marginBottom: '0.75rem' }}>
            High-level enrollment and activity patterns over the last 180 days.
          </p>
          <LmsOrgTrendChartsPanel days={180} />
        </section>

        <hr className="lms-divider" />

        <section className="lms-section" aria-labelledby="lms-org-atrisk-heading">
          <h2 id="lms-org-atrisk-heading" className="lms-section__title">
            At-risk learners
          </h2>
          <p className="lms-help-text" style={{ marginBottom: '0.75rem' }}>
            Review learners flagged by progress rules and add notes for your team.
          </p>
          <LmsOrgAtRiskPanel />
        </section>

        <hr className="lms-divider" />

        <section className="lms-section" aria-labelledby="lms-org-ldap-heading">
          <h2 id="lms-org-ldap-heading" className="lms-section__title">
            Directory sync
          </h2>
          <p className="lms-help-text" style={{ marginBottom: '0.75rem' }}>
            Configure LDAP sources and run syncs so rosters stay aligned with your directory.
          </p>
          <LmsOrgLdapSourcesPanel />
        </section>

        <nav className="lms-footer-links" aria-label="Related pages">
          <a href="/courses">Course catalog</a>
          {' · '}
          <a href="/my/teaching">My teaching</a>
          {' · '}
          <a href="/my/learning">My learning</a>
        </nav>
      </div>
    </Page>
  );
}
