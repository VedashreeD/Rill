import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, API_BASE } from "../api/client";
import LocationArt from "../components/LocationArt";
import TierBadge from "../components/TierBadge";
import type { MlStatus, ReportItem, WorldLocation } from "../types";

const CONDITION_LABELS: Record<string, string> = {
  clear: "Clear",
  murky: "Murky",
  flooded: "Flooded",
  whitewater: "Whitewater",
  algae: "Algae",
  debris: "Debris",
};

export default function LocationDetail() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();

  const [allLocations, setAllLocations] = useState<WorldLocation[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [mlStatus, setMlStatus] = useState<MlStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!code) return;
    setLoading(true);
    setError(null);
    try {
      const [locs, reps, status] = await Promise.all([
        api.listLocations(),
        api.listReports({ segmentCode: code }),
        api.getMlStatus(),
      ]);
      setAllLocations(locs);
      setReports(reps);
      setMlStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to load location");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  const location = allLocations.find((l) => l.code === code) ?? null;

  function locationName(segCode: string): string {
    return allLocations.find((l) => l.code === segCode)?.name ?? segCode;
  }

  if (loading && !location) {
    return (
      <div className="location-detail-page">
        <p className="muted">Loading…</p>
      </div>
    );
  }

  if (!location) {
    return (
      <div className="location-detail-page">
        <p className="form-error">Unknown location.</p>
        <button className="btn-ghost" onClick={() => navigate("/overview")}>
          Back to Overview
        </button>
      </div>
    );
  }

  return (
    <div className="location-detail-page">
      <button className="link-btn" onClick={() => navigate("/overview")}>
        ← Back to Overview
      </button>

      <div className="location-detail-header">
        <LocationArt variant={location.illustration} className="location-detail-art" />
        <div>
          <span className="segment-tag">{location.code}</span>
          <h1>{location.name}</h1>
          <p className="report-sub">{location.description}</p>
          <div className="location-detail-stats">
            <TierBadge tier={location.currentTier} />
            <span>{location.reportCount} reports</span>
            <span>{location.imageCount} images</span>
          </div>
        </div>
      </div>

      {mlStatus && !mlStatus.trained && (
        <div className="ml-status-banner">
          Condition classification isn't showing below because no trained model has been
          found yet. To enable it: <code>{mlStatus.instructions}</code>
        </div>
      )}

      {error && <p className="form-error">{error}</p>}

      <h2>Reports</h2>
      {reports.length === 0 ? (
        <p className="muted">No reports yet for this location.</p>
      ) : (
        <ul className="location-report-list">
          {reports.map((r) => (
            <li key={r.id} className="location-report-card">
              {r.imagePath && (
                <img
                  src={`${API_BASE}${r.imagePath}`}
                  alt="Uploaded report"
                  className="location-report-image"
                />
              )}
              <div className="location-report-body">
                <div className="location-report-meta">
                  <time className="report-time">{new Date(r.createdAt).toLocaleString()}</time>
                  <TierBadge tier={r.classification.tier} />
                </div>

                <p className="report-desc">{r.description || "No notes provided."}</p>

                <div className="model-output-block">
                  <span className="model-output-label">AI condition classification:</span>
                  {r.condition ? (
                    <ul className="condition-breakdown">
                      {r.condition.scores.map((s, i) => (
                        <li
                          key={s.label}
                          className={`condition-score-row${i === 0 ? " condition-score-top" : ""}`}
                        >
                          <span className="condition-score-label">
                            {CONDITION_LABELS[s.label] ?? s.label}
                          </span>
                          <span className="condition-score-bar-track">
                            <span
                              className="condition-score-bar-fill"
                              style={{ width: `${Math.max(0, Math.round(s.similarity * 100))}%` }}
                            />
                          </span>
                          <span className="condition-score-value">
                            {Math.round(s.similarity * 100)}%
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="muted">not available</span>
                  )}
                </div>

                {r.visualMatches.length > 0 && (
                  <div className="visual-matches">
                    <span className="visual-matches-label">Also visually resembles:</span>
                    {r.visualMatches.map((m) => (
                      <span key={m.segmentCode} className="visual-match-chip">
                        {locationName(m.segmentCode)} ({Math.round(m.similarity * 100)}%)
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
