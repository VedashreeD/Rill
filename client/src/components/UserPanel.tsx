import { useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { AlertRecord, AlertSettings, Tier, WorldLocation } from "../types";

const TIER_OPTIONS: { value: Tier; label: string }[] = [
  { value: "watch", label: "Watch and above" },
  { value: "caution", label: "Caution and above" },
  { value: "emergency", label: "Emergency only" },
];

const CHANNEL_OPTIONS: { value: string; label: string }[] = [
  { value: "push", label: "Push notifications" },
  { value: "sms", label: "SMS" },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function UserPanel({ open, onClose }: Props) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [settings, setSettings] = useState<AlertSettings | null>(null);
  const [locations, setLocations] = useState<WorldLocation[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    setSaved(false);
    Promise.all([api.me(), api.listLocations(), api.listMyAlerts()])
      .then(([me, locs, alertHistory]) => {
        setSettings(me.alertSettings);
        setLocations(locs);
        setAlerts(alertHistory);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "failed to load"))
      .finally(() => setLoading(false));
  }, [open]);

  function toggleChannel(channel: string) {
    if (!settings) return;
    const has = settings.channels.includes(channel);
    setSettings({
      ...settings,
      channels: has
        ? settings.channels.filter((c) => c !== channel)
        : [...settings.channels, channel],
    });
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await api.updateAlertSettings(settings);
      setSettings(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    logout();
    onClose();
    navigate("/login");
  }

  if (!open) return null;

  return createPortal(
    <div className="settings-overlay" onClick={onClose}>
      <aside className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Account</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {loading && <p className="muted">Loading…</p>}
        {error && <p className="form-error">{error}</p>}

        {!loading && settings && (
          <>
            <section className="panel-section">
              <h3>Watch settings</h3>
              <form className="settings-form" onSubmit={handleSave}>
                <div className="settings-group">
                  <span className="settings-label">Notify me by</span>
                  {CHANNEL_OPTIONS.map((c) => (
                    <label key={c.value} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={settings.channels.includes(c.value)}
                        onChange={() => toggleChannel(c.value)}
                      />
                      {c.label}
                    </label>
                  ))}
                </div>

                <div className="settings-group">
                  <span className="settings-label">Minimum tier to notify</span>
                  <select
                    value={settings.minTier}
                    onChange={(e) =>
                      setSettings({ ...settings, minTier: e.target.value as Tier })
                    }
                  >
                    {TIER_OPTIONS.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="settings-group">
                  <span className="settings-label">Home location</span>
                  <select
                    value={settings.homeSegmentCode ?? ""}
                    onChange={(e) =>
                      setSettings({ ...settings, homeSegmentCode: e.target.value || null })
                    }
                  >
                    <option value="">No home location set</option>
                    {locations.map((loc) => (
                      <option key={loc.code} value={loc.code}>
                        {loc.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="settings-group">
                  <span className="settings-label">
                    Radius: {(settings.radiusMeters / 1000).toFixed(1)} km around home location
                  </span>
                  <input
                    type="range"
                    min={500}
                    max={20000}
                    step={500}
                    value={settings.radiusMeters}
                    onChange={(e) =>
                      setSettings({ ...settings, radiusMeters: Number(e.target.value) })
                    }
                  />
                </div>

                {saved && <p className="form-success">Settings saved.</p>}

                <button className="btn-primary" type="submit" disabled={saving}>
                  {saving ? "Saving…" : "Save settings"}
                </button>
              </form>
            </section>

            <section className="panel-section">
              <h3>Past alerts</h3>
              {alerts.length === 0 ? (
                <p className="muted">No alerts sent yet.</p>
              ) : (
                <ul className="alert-history-list">
                  {alerts.map((a) => (
                    <li key={a.id} className="alert-history-item">
                      <span className={`tier-badge tier-${a.tier}`}>{a.tier}</span>
                      <div>
                        <p className="alert-message">{a.message}</p>
                        <time className="report-time">
                          {new Date(a.sentAt).toLocaleString()}
                        </time>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="panel-section">
              <h3>Account</h3>
              <p className="account-username">Signed in as <strong>{user?.username}</strong></p>
              <button className="btn-ghost" onClick={handleLogout}>
                Log out
              </button>
            </section>
          </>
        )}
      </aside>
    </div>,
    document.body
  );
}
