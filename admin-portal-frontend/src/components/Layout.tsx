import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const Layout = ({ children }: { children: React.ReactNode }) => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Admin Portal</h1>
        <div className="nav-links">
          <NavLink to="/clinics" className={({ isActive }) => (isActive ? "active" : "")}>
            Clinics
          </NavLink>
          <NavLink to="/doctors" className={({ isActive }) => (isActive ? "active" : "")}>
            Doctors
          </NavLink>
          <button className="secondary" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
};

export default Layout;
