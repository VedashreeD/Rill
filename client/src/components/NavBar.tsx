import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import UserPanel from "./UserPanel";

export default function NavBar() {
  const { user } = useAuth();
  const [panelOpen, setPanelOpen] = useState(false);

  const initial = user?.username?.[0]?.toUpperCase() ?? "?";

  return (
    <header className="navbar">
      <div className="navbar-left">
        <div className="navbar-brand">
          <div className="brand-icon">
            <svg viewBox="0 0 24 24">
              <path d="M2 12c3-3 6-3 9 0s6 3 9 0M2 17c3-3 6-3 9 0s6 3 9 0" />
            </svg>
          </div>
          <span>Rill</span>
          <span className="brand-tag">v2.4 TELEMETRY</span>
        </div>
        <div className="live-indicator">
          <span className="pulse-dot" />
          <span>ML INFERENCE ACTIVE</span>
        </div>
      </div>

      {user && (
        <nav className="navbar-center">
          <NavLink to="/overview" className={({ isActive }) => (isActive ? "active" : "")}>
            Overview
          </NavLink>
          <NavLink to="/report" className={({ isActive }) => (isActive ? "active" : "")}>
            Report Incident
          </NavLink>
        </nav>
      )}

      <div className="navbar-right">
        {user && (
          <button
            className="user-pill-btn"
            onClick={() => setPanelOpen(true)}
            aria-label="Open account menu"
            title={user.username}
          >
            <div className="avatar-circle">{initial}</div>
            <span className="user-pill-name">{initial}</span>
          </button>
        )}
      </div>

      <UserPanel open={panelOpen} onClose={() => setPanelOpen(false)} />
    </header>
  );
}
