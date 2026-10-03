import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, API_BASE } from "../api/client";
import LocationArt from "../components/LocationArt";
import TierBadge from "../components/TierBadge";
import type { Tier, WorldLocation } from "../types";

const TIER_FILTERS: { value: Tier | ""; label: string }[] = [
  { value: "", label: "All locations" },
  { value: "watch", label: "Watch and above" },
  { value: "caution", label: "Caution and above" },
  { value: "emergency", label: "Emergency only" },
];

const TIER_ORDER: Tier[] = ["green", "watch", "caution", "emergency"];

export default function RillOverview() {
  const navigate = useNavigate();
  const [locations, setLocations] = useState<WorldLocation[]>([]);
  const [minTier, setMinTier] = useState<Tier | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const locs = await api.listLocations();
      setLocations(locs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to load locations");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  const stats = useMemo(() => {
    const totalReports = locations.reduce((sum, l) => sum + l.reportCount, 0);
    const totalImages = locations.reduce((sum, l) => sum + l.imageCount, 0);
    const byTier: Record<Tier, number> = { green: 0, watch: 0, caution: 0, emergency: 0 };
    for (const l of locations) {
      if (l.currentTier) byTier[l.currentTier] += 1;
    }
    return { totalReports, totalImages, byTier };
  }, [locations]);

  const visibleLocations = useMemo(() => {
    if (!minTier) return locations;
    const minIndex = TIER_ORDER.indexOf(minTier);
    return locations.filter((l) => l.currentTier && TIER_ORDER.indexOf(l.currentTier) >= minIndex);
  }, [locations, minTier]);

  return (
    <div className="overview-page">
      <div className="overview-header">
        <div className="overview-title-group">
          <h1>Stream Intelligence</h1>
          <p className="overview-sub">
            Real-time telemetry, vision classification, and risk tier monitoring across all segments.
          </p>
        </div>
        <select
          className="tier-filter-select"
          value={minTier}
          onChange={(e) => setMinTier(e.target.value as Tier | "")}
        >
          {TIER_FILTERS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      <div className="stat-strip">
        <div className="stat-card">
          <div className="stat-card-accent-bar" />
          <span className="stat-value">{locations.length}</span>
          <span className="stat-label">Monitored Segments</span>
        </div>
        <div className="stat-card">
          <div className="stat-card-accent-bar" />
          <span className="stat-value">{stats.totalReports}</span>
          <span className="stat-label">Telemetry Reports</span>
        </div>
        <div className="stat-card">
          <div className="stat-card-accent-bar" />
          <span className="stat-value">{stats.totalImages}</span>
          <span className="stat-label">Captured Imagery</span>
        </div>
        <div className="stat-card stat-card-tiers">
          <div className="stat-card-accent-bar" />
          <div className="stat-tier-rows">
            <TierBadge tier="green" />
            <span>{stats.byTier.green}</span>
          </div>
          <div className="stat-tier-rows">
            <TierBadge tier="watch" />
            <span>{stats.byTier.watch}</span>
          </div>
          <div className="stat-tier-rows">
            <TierBadge tier="caution" />
            <span>{stats.byTier.caution}</span>
          </div>
          <div className="stat-tier-rows">
            <TierBadge tier="emergency" />
            <span>{stats.byTier.emergency}</span>
          </div>
        </div>
      </div>

      {loading && locations.length === 0 && <p className="muted">Loading telemetry data…</p>}
      {error && <p className="form-error">{error}</p>}

      <div className="location-grid">
        {visibleLocations.map((loc) => (
          <button
            key={loc.code}
            className="location-card location-card-clickable"
            onClick={() => navigate(`/overview/${loc.code}`)}
          >
            <div className="location-art-container">
              {loc.latestImagePath ? (
                <img
                  src={`${API_BASE}${loc.latestImagePath}`}
                  alt={`Latest photo for ${loc.name}`}
                  className="location-art"
                />
              ) : (
                <LocationArt variant={loc.illustration} className="location-art" />
              )}
            </div>
            <div className="location-card-body">
              <div className="location-card-top">
                <span className="segment-tag">{loc.code}</span>
                <TierBadge tier={loc.currentTier} />
              </div>
              <h3>{loc.name}</h3>
              <p className="location-desc">{loc.description}</p>
              <div className="location-stats-row">
                <span>📊 {loc.reportCount} telemetry reports</span>
                <span>📷 {loc.imageCount} images</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
