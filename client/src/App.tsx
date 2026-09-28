import { Routes, Route, Navigate } from "react-router-dom";
import type { ReactElement } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import NavBar from "./components/NavBar";
import Login from "./pages/Login";
import Register from "./pages/Register";
import RillReport from "./pages/RillReport";
import RillOverview from "./pages/RillOverview";
import LocationDetail from "./pages/LocationDetail";

function RequireAuth({ children }: { children: ReactElement }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
}

function Shell() {
  return (
    <div className="app-shell">
      <NavBar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/report"
            element={
              <RequireAuth>
                <RillReport />
              </RequireAuth>
            }
          />
          <Route
            path="/overview"
            element={
              <RequireAuth>
                <RillOverview />
              </RequireAuth>
            }
          />
          <Route
            path="/overview/:code"
            element={
              <RequireAuth>
                <LocationDetail />
              </RequireAuth>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}
