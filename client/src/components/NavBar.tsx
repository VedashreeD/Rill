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
      <div className="navbar-side navbar-side-left">
        <div className="navbar-brand">Rill</div>
      </div>

      {user && (
        <nav className="navbar-links navbar-center">
          <NavLink to="/report" className={({ isActive }) => (isActive ? "active" : "")}>
            Report
          </NavLink>
          <NavLink to="/overview" className={({ isActive }) => (isActive ? "active" : "")}>
            Overview
          </NavLink>
        </nav>
      )}

      <div className="navbar-side navbar-side-right">
        {user && (
          <button
            className="avatar-btn"
            onClick={() => setPanelOpen(true)}
            aria-label="Open account menu"
            title={user.username}
          >
            {initial}
          </button>
        )}
      </div>

      <UserPanel open={panelOpen} onClose={() => setPanelOpen(false)} />
    </header>
  );
}
