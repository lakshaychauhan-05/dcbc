import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Clinics from "./pages/Clinics";
import Doctors from "./pages/Doctors";
import { useAuth } from "./hooks/useAuth";

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return <div style={{ padding: 24 }}>Loading...</div>;
  }
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
};

const AppRoutes = () => (
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route
      path="/clinics"
      element={
        <ProtectedRoute>
          <Layout>
            <Clinics />
          </Layout>
        </ProtectedRoute>
      }
    />
    <Route
      path="/doctors"
      element={
        <ProtectedRoute>
          <Layout>
            <Doctors />
          </Layout>
        </ProtectedRoute>
      }
    />
    <Route path="/" element={<Navigate to="/clinics" replace />} />
    <Route path="*" element={<Navigate to="/clinics" replace />} />
  </Routes>
);

const App = () => <AppRoutes />;

export default App;
