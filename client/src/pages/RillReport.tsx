import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import LocationArt from "../components/LocationArt";
import type { ReportItem, WorldLocation } from "../types";

export default function RillReport() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const segmentParam = searchParams.get("segment");

  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<ReportItem | null>(null);
  const [locations, setLocations] = useState<WorldLocation[]>([]);
  const [locationsLoaded, setLocationsLoaded] = useState(false);

  // Manual selection — the second intake path, alongside scanning a QR
  // code. Not a fallback: nothing here ever substitutes a guessed or
  // random location. It's a deliberate choice the person makes, exactly
  // as legitimate as a scanned code, and it produces the same required,
  // validated segmentCode create_report() expects — the backend can't
  // tell the two paths apart, and doesn't need to.
  const [manuallyPicked, setManuallyPicked] = useState("");

  useEffect(() => {
    api
      .listLocations()
      .then(setLocations)
      .catch(() => setLocations([]))
      .finally(() => setLocationsLoaded(true));
  }, []);

  const scannedSegment = segmentParam
    ? locations.find((l) => l.code === segmentParam) ?? null
    : null;
  const pickedSegment = manuallyPicked
    ? locations.find((l) => l.code === manuallyPicked) ?? null
    : null;

  // A QR scan takes priority if present and valid — the manual picker only
  // matters when there's no QR context at all (e.g. opening Rill Report
  // straight from the nav bar).
  const activeSegment = scannedSegment ?? pickedSegment;

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    // Defense in depth — the form below only renders when activeSegment is
    // set, but this guards against that ever becoming stale.
    if (!activeSegment) {
      setError("Select a location before submitting.");
      return;
    }
    if (!description && !file) {
      setError("Add a photo, a description, or both.");
      return;
    }

    setBusy(true);
    try {
      const formData = new FormData();
      formData.append("description", description);
      formData.append("segmentCode", activeSegment.code);
      if (file) formData.append("image", file);

      const report = await api.createReport(formData);
      setSubmitted(report);
      setDescription("");
      setFile(null);
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to send report");
    } finally {
      setBusy(false);
    }
  }

  if (submitted) {
    const assignedLocation = locations.find((l) => l.code === submitted.segmentCode);
    return (
      <div className="report-page">
        <div className="report-card">
          <div className="segment-chip">Report sent</div>
          <h1>Thank you</h1>
          {assignedLocation && (
            <>
              <LocationArt variant={assignedLocation.illustration} className="confirmation-art" />
              <p className="report-sub">
                This was logged at <strong>{assignedLocation.name}</strong>.
              </p>
            </>
          )}
          <button className="btn-primary" onClick={() => setSubmitted(null)}>
            Send another report
          </button>
          <button type="button" className="btn-ghost" onClick={() => navigate("/overview")}>
            View Rill Overview
          </button>
        </div>
      </div>
    );
  }

  if (!locationsLoaded) {
    return (
      <div className="report-page">
        <div className="report-card">
          <p className="muted">Loading…</p>
        </div>
      </div>
    );
  }

  // No QR scanned (or an unrecognized code) — offer manual selection
  // instead of blocking outright. This is the picker, not a fallback.
  if (!scannedSegment && !pickedSegment) {
    return (
      <div className="report-page">
        <div className="report-card">
          <h1>Rill Report</h1>
          <p className="report-sub">
            {segmentParam
              ? "That QR code's location wasn't recognized. Scan a valid Rill Report QR code, or select your location below."
              : "Scan a Rill Report QR code at a monitored site, or select your location below if you're reporting from the webpage directly."}
          </p>

          <label className="location-picker-label">
            Location
            <select
              value={manuallyPicked}
              onChange={(e) => setManuallyPicked(e.target.value)}
            >
              <option value="">Choose a location…</option>
              {locations.map((loc) => (
                <option key={loc.code} value={loc.code}>
                  {loc.name}
                </option>
              ))}
            </select>
          </label>

          <button type="button" className="btn-ghost" onClick={() => navigate("/overview")}>
            View Rill Overview instead
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="report-page">
      <div className="report-card">
        <div className="segment-chip">{activeSegment!.code}</div>
        <LocationArt variant={activeSegment!.illustration} className="confirmation-art" />
        <h1>Reporting at {activeSegment!.name}</h1>
        <p className="report-sub">{activeSegment!.description}</p>
        {pickedSegment && !scannedSegment && (
          <button
            type="button"
            className="link-btn"
            onClick={() => setManuallyPicked("")}
          >
            Change location
          </button>
        )}

        <form onSubmit={handleSubmit} className="report-form">
          <label className="photo-input">
            {preview ? (
              <img src={preview} alt="Preview of the uploaded report" className="photo-preview" />
            ) : (
              <div className="photo-placeholder">
                <span>Tap to add a photo</span>
              </div>
            )}
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileChange}
              hidden
            />
          </label>

          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="e.g. Water is rising fast past the bridge marker"
            />
          </label>

          {error && <p className="form-error">{error}</p>}

          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? "Sending…" : "Send report"}
          </button>
          <button type="button" className="btn-ghost" onClick={() => navigate("/overview")}>
            View Rill Overview instead
          </button>
        </form>
      </div>
    </div>
  );
}
