import {
  ChartNoAxesCombined,
  FolderKanban,
  LogOut,
  Moon,
  Settings,
  Sun,
} from "lucide-react";

import { useState } from "react";

import {
  NavLink,
  Outlet,
  useLocation,
} from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { usePermissions } from "../auth/usePermissions";
import { useScanHiveTheme } from "../theme/ScanHiveThemeProvider";
import { BrandMark } from "../components/BrandMark";

export function AppLayout() {
  const { logout } = useAuth();
  const location = useLocation();
  const { mode: theme, toggle: toggleTheme } = useScanHiveTheme();
  const [isCollapsed, setCollapsed] = useState(false);
  const { hasPermission, profile } = usePermissions();
  const canViewDashboard = hasPermission("analytics.dashboard");

  return (
    <div className={`app-shell ${isCollapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="brand">
          <button
            type="button"
            className="brand-icon"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setCollapsed((current) => !current)}
          >
            <BrandMark size={25} />
          </button>

          <div>
            <strong>ScanHive</strong>
            <span>{profile?.organization_name ?? "Security Dashboard"}</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {canViewDashboard && (
            <NavLink
              to="/dashboard"
              className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
            >
              <ChartNoAxesCombined size={19} />
              <span>Dashboard</span>
            </NavLink>
          )}
          <NavLink
            to="/projects"
            className={({ isActive }) =>
              isActive
                ? "nav-link active"
                : "nav-link"
            }
          >
            <FolderKanban size={19} />
            <span>Projects</span>
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <NavLink
            to="/settings/iam?section=organization"
            className={location.pathname.startsWith("/settings") ? "nav-link active" : "nav-link"}
          >
            <Settings size={19} />
            <span>Settings</span>
          </NavLink>

          <button
            type="button"
            className="theme-toggle-button"
            onClick={toggleTheme}
          >
            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            <span>{theme === "light" ? "Night theme" : "Light theme"}</span>
          </button>

          <button
            type="button"
            className="logout-button"
            onClick={logout}
          >
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
