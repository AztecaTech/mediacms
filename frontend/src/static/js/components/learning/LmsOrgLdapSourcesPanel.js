import React, { useCallback, useEffect, useState } from 'react';
import { lmsGetJson, lmsPostJson } from '../../utils/helpers/lmsApi';

export function LmsOrgLdapSourcesPanel() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncingId, setSyncingId] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    lmsGetJson('/admin/directory/ldap-sources/')
      .then(setRows)
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onSync = async (id) => {
    setSyncingId(id);
    setError(null);
    try {
      await lmsPostJson(`/admin/directory/ldap-sources/${id}/sync/`, {});
      await load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSyncingId(null);
    }
  };

  return (
    <section className="lms-org-ldap" aria-labelledby="lms-org-ldap-heading">
      <h2 id="lms-org-ldap-heading" className="lms-subheading">
        LDAP directory sources
      </h2>
      <p className="lms-hint">
        Profiles are created in Django admin. Sync currently updates status only until ldap3 import is
        implemented.
      </p>
      {error ? <p className="error-message">{error}</p> : null}
      {loading ? <p>Loading…</p> : null}
      {!loading && !rows.length ? <p>No LDAP sources configured.</p> : null}
      {rows.length ? (
        <ul className="lms-ldap-source-list">
          {rows.map((s) => (
            <li key={s.id} style={{ marginBottom: '0.75rem' }}>
              <strong>{s.name}</strong>{' '}
              <span className="lms-meta">
                {s.server_uri} — {s.enabled ? 'enabled' : 'disabled'}
              </span>
              <br />
              <span className="lms-meta">
                Last sync: {s.last_sync_at || 'never'}
                {s.last_sync_message ? ` — ${s.last_sync_message}` : ''}
              </span>
              <br />
              <button
                type="button"
                className="btn btn-secondary"
                style={{ marginTop: '0.25rem' }}
                disabled={syncingId === s.id}
                onClick={() => onSync(s.id)}
              >
                {syncingId === s.id ? 'Syncing…' : 'Run sync'}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
