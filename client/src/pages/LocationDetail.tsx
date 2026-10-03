import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, API_BASE } from "../api/client";
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
  const [taggingReportId, setTaggingReportId] = useState<string | null>(null);
  const [tagFeedbackId, setTagFeedbackId] = useState<string | null>(null);

  async function refresh(silent: boolean = false) {
    if (!code) return;
    if (!silent) setLoading(true);
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
      if (!silent) setLoading(false);
    }
  }

  async function handleTag(reportId: string, tag: string) {
    setTaggingReportId(reportId);
    try {
      const updated = await api.tagReportCondition(reportId, tag);
      setReports((prev) => prev.map((r) => (r.id === reportId ? updated : r)));
      setTagFeedbackId(reportId);
      setTimeout(() => setTagFeedbackId(null), 5000);
      setTimeout(() => {
        refresh(true);
      }, 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to tag report");
    } finally {
      setTaggingReportId(null);
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

  // Calculate condition trend directly based on uploaded images/reports
  const imageTrend = useMemo(() => {
    // Sort reports chronologically (oldest to newest)
    const sorted = reports
      .slice()
      .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());

    return sorted.map((r, idx) => {
      const d = new Date(r.createdAt);
      const dateStr = isNaN(d.getTime())
        ? `Report #${idx + 1}`
        : d.toLocaleDateString("en-US", { month: "short", day: "numeric" });

      const topScore = r.condition?.scores?.[0];
      const condition = topScore ? topScore.label : null;
      const scorePct = topScore ? Math.round(topScore.similarity * 100) : 0;

      return {
        id: r.id,
        index: idx + 1,
        dateStr,
        condition,
        scorePct,
        hasImage: Boolean(r.imagePath),
      };
    });
  }, [reports]);

  const groupedReports = useMemo(() => {
    const groups: { dateKey: string; dateLabel: string; items: ReportItem[] }[] = [];
    for (const r of reports) {
      const d = new Date(r.createdAt);
      const dateKey = isNaN(d.getTime()) ? "unknown" : d.toISOString().split("T")[0];
      const dateLabel = isNaN(d.getTime())
        ? "Unknown Date"
        : d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });

      let group = groups.find((g) => g.dateKey === dateKey);
      if (!group) {
        group = { dateKey, dateLabel, items: [] };
        groups.push(group);
      }
      group.items.push(r);
    }
    return groups;
  }, [reports]);

  if (loading && !location) {
    return (
      <div className="location-detail-page">
        <p className="muted">Loading telemetry data…</p>
      </div>
    );
  }

  if (!location) {
    return (
      <div className="location-detail-page">
        <p className="form-error">Unknown location segment.</p>
        <button className="btn-ghost" onClick={() => navigate("/overview")}>
          ← Back to Overview
        </button>
      </div>
    );
  }

  return (
    <div className="location-detail-page">
      <button className="link-btn" onClick={() => navigate("/overview")}>
        ← Back to Overview
      </button>

      {/* Imagery Condition Trend Graph */}
      <div className="weekly-trend-card">
        <div className="weekly-trend-header">
          <div className="weekly-trend-title">
            <span className="segment-tag">{location.code}</span>
            <h2>{location.name} — Imagery Condition Trend</h2>
          </div>
          <TierBadge tier={location.currentTier} />
        </div>

        {imageTrend.length === 0 ? (
          <p className="muted">No telemetry images uploaded yet to compute trend.</p>
        ) : (
          <div className="image-trend-chart">
            {imageTrend.map((item) => (
              <div key={item.id} className="trend-bar-col">
                <div className="trend-bar-track">
                  <div
                    className={`trend-bar-fill ${item.condition ? `condition-bg-${item.condition}` : "trend-empty"}`}
                    style={{ height: `${item.scorePct > 0 ? Math.max(16, item.scorePct) : 8}%` }}
                  >
                    {item.scorePct > 0 && <span className="trend-score-pop">{item.scorePct}%</span>}
                  </div>
                </div>
                <span className="trend-day-label">Img #{item.index}</span>
                <span className="trend-cond-label">
                  {item.condition ? CONDITION_LABELS[item.condition] ?? item.condition : "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {mlStatus && !mlStatus.trained && (
        <div className="ml-status-banner">
          Condition classification is currently offline. Model status: <code>{mlStatus.instructions}</code>
        </div>
      )}

      {error && <p className="form-error">{error}</p>}

      <h2>Telemetry Timeline</h2>
      {groupedReports.length === 0 ? (
        <p className="muted">No telemetry reports recorded for this segment.</p>
      ) : (
        <div className="date-grouped-timeline">
          {groupedReports.map((group) => (
            <div key={group.dateKey} className="date-group-section">
              <div className="date-group-divider">
                <span className="date-group-label">🗓️ {group.dateLabel}</span>
                <span className="date-group-line" />
              </div>

              <div className="location-report-list">
                {group.items.map((r) => {
                  const timeStr = new Date(r.createdAt).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                  });

                  return (
                    <div key={r.id} className="location-report-card">
                      <div className="report-card-main">
                        {r.imagePath ? (
                          <div className="location-report-image-wrap">
                            <img
                              src={`${API_BASE}${r.imagePath}`}
                              alt={`Photo taken at ${timeStr}`}
                              className="location-report-image"
                            />
                            <div className="report-image-timestamp">
                              🕒 {timeStr}
                            </div>
                          </div>
                        ) : (
                          <div className="report-no-image-time">
                            🕒 Captured at {timeStr}
                          </div>
                        )}

                        <div className="location-report-body">
                          <div className="location-report-meta">
                            <span className="model-output-label">Assigned Tier:</span>
                            <TierBadge tier={r.classification.tier} />
                          </div>

                          <p className="report-desc">{r.description || "No observation notes attached."}</p>

                          <div className="model-output-block">
                            <span className="model-output-label">AI Condition Analysis:</span>
                            {r.condition ? (
                              <ul className="condition-breakdown">
                                {r.condition.scores.map((s, i) => {
                                  const pct = Math.max(0, Math.min(100, Math.round(s.similarity * 100)));
                                  return (
                                    <li
                                      key={s.label}
                                      className={`condition-score-row${i === 0 ? " condition-score-top" : ""}`}
                                    >
                                      <span className="condition-score-label">
                                        {CONDITION_LABELS[s.label] ?? s.label}
                                      </span>
                                      <div className="condition-score-bar-track">
                                        <div
                                          className="condition-score-bar-fill"
                                          style={{ width: `${pct}%` }}
                                        />
                                      </div>
                                      <span className="condition-score-value">{pct}%</span>
                                    </li>
                                  );
                                })}
                              </ul>
                            ) : (
                              <span className="muted">Pending classification</span>
                            )}
                          </div>

                          {r.visualMatches.length > 0 && (
                            <div className="visual-matches">
                              <span className="model-output-label">Visual similarity:</span>
                              {r.visualMatches.map((m) => (
                                <span key={m.segmentCode} className="visual-match-chip">
                                  {locationName(m.segmentCode)} ({Math.round(m.similarity * 100)}%)
                                </span>
                              ))}
                            </div>
                          )}

                          {r.imagePath && (
                            <div className="condition-feedback-section">
                              <div className="condition-feedback-header">
                                <span className="model-output-label">
                                  {r.userTag ? "Verified condition:" : "Active Learning — Tag true condition:"}
                                </span>
                                {r.userTag && (
                                  <span className="user-tag-badge">
                                    ✓ {CONDITION_LABELS[r.userTag] ?? r.userTag}
                                  </span>
                                )}
                              </div>
                              <div className="condition-tag-buttons">
                                {Object.entries(CONDITION_LABELS).map(([key, label]) => (
                                  <button
                                    key={key}
                                    type="button"
                                    className={`btn-tag ${r.userTag === key ? "btn-tag-active" : ""}`}
                                    disabled={taggingReportId === r.id}
                                    onClick={() => handleTag(r.id, key)}
                                  >
                                    {label}
                                  </button>
                                ))}
                              </div>
                              {tagFeedbackId === r.id && (
                                <p className="tag-feedback-note">
                                  ✓ Tag saved! Model is retraining in background.
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
