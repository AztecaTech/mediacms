import { lmsGetJson, lmsPostJson } from '../../../utils/helpers/lmsApi';

/**
 * Loads org at-risk rows and posts manager intervention notes (API calls only).
 */
export class OrgAtRiskListViewModel {
  load(minTier, limit) {
    const q = new URLSearchParams({ min_tier: minTier, limit: String(limit) });
    return lmsGetJson(`/admin/analytics/at-risk-enrollments/?${q}`);
  }

  postInterventionNote(enrollmentId, note) {
    return lmsPostJson('/admin/analytics/intervention-notes/', {
      enrollment_id: enrollmentId,
      note,
    });
  }
}
