import React from 'react';
import { LmsOrgAtRiskPanel } from '../components/learning/LmsOrgAtRiskPanel';
import { LmsOrgLdapSourcesPanel } from '../components/learning/LmsOrgLdapSourcesPanel';
import { LmsOrgTrendChartsPanel } from '../components/learning/LmsOrgTrendChartsPanel';
import { Page } from './Page';

export function OrgManagerLearningPage({ id = 'lms_org_learning' }) {
  return (
    <Page id={id}>
      <div className="lms-page lms-org-learning">
        <h1 className="page-title">Org learning</h1>
        <p className="lms-hint">Manager tools: at-risk learners and directory sync profiles.</p>
        <LmsOrgTrendChartsPanel days={180} />
        <hr style={{ margin: '2rem 0', border: 0, borderTop: '1px solid rgba(0,0,0,0.08)' }} />
        <LmsOrgAtRiskPanel />
        <hr style={{ margin: '2rem 0', border: 0, borderTop: '1px solid rgba(0,0,0,0.08)' }} />
        <LmsOrgLdapSourcesPanel />
        <p style={{ marginTop: '1.5rem' }}>
          <a href="/courses">Course catalog</a>
          {' · '}
          <a href="/my/teaching">My teaching</a>
        </p>
      </div>
    </Page>
  );
}
