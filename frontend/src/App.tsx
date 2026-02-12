import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';

// Contexts
import { DoctorAuthProvider, useDoctorAuth } from './contexts/DoctorAuthContext';
import { AdminAuthProvider, useAdminAuth } from './contexts/AdminAuthContext';

// Pages
import Home from './pages/Home';
import DoctorLogin from './pages/doctor/Login';
import DoctorOAuthCallback from './pages/doctor/OAuthCallback';
import DoctorDashboard from './pages/doctor/Dashboard';
import DoctorAppointments from './pages/doctor/Appointments';
import DoctorPatients from './pages/doctor/Patients';
import DoctorPatientDetail from './pages/doctor/PatientDetail';
import DoctorSettings from './pages/doctor/Settings';
import AdminLogin from './pages/admin/Login';
import AdminDashboard from './pages/admin/Dashboard';
import AdminClinics from './pages/admin/Clinics';
import AdminDoctors from './pages/admin/Doctors';

// Layouts
import DoctorLayout from './components/doctor/Layout';
import AdminLayout from './components/admin/Layout';

// Protected Route for Doctor Portal
const DoctorProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token, loading } = useDoctorAuth();
  const location = useLocation();

  if (loading) {
    return (
      <Box minHeight="100vh" display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
      </Box>
    );
  }

  if (!token) {
    return <Navigate to="/doctor/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

// Protected Route for Admin Portal
const AdminProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token, loading } = useAdminAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-content">
          <span className="spinner spinner-lg" aria-hidden />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

// Doctor Portal Routes
const DoctorRoutes = () => (
  <DoctorAuthProvider>
    <Routes>
      <Route path="login" element={<DoctorLogin />} />
      <Route path="oauth/callback" element={<DoctorOAuthCallback />} />
      <Route
        path="/"
        element={
          <DoctorProtectedRoute>
            <DoctorLayout><DoctorDashboard /></DoctorLayout>
          </DoctorProtectedRoute>
        }
      />
      <Route
        path="dashboard"
        element={
          <DoctorProtectedRoute>
            <DoctorLayout><DoctorDashboard /></DoctorLayout>
          </DoctorProtectedRoute>
        }
      />
      <Route
        path="appointments"
        element={
          <DoctorProtectedRoute>
            <DoctorLayout><DoctorAppointments /></DoctorLayout>
          </DoctorProtectedRoute>
        }
      />
      <Route
        path="patients"
        element={
          <DoctorProtectedRoute>
            <DoctorLayout><DoctorPatients /></DoctorLayout>
          </DoctorProtectedRoute>
        }
      />
      <Route
        path="patients/:id"
        element={
          <DoctorProtectedRoute>
            <DoctorLayout><DoctorPatientDetail /></DoctorLayout>
          </DoctorProtectedRoute>
        }
      />
      <Route
        path="settings"
        element={
          <DoctorProtectedRoute>
            <DoctorLayout><DoctorSettings /></DoctorLayout>
          </DoctorProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/doctor/dashboard" replace />} />
    </Routes>
  </DoctorAuthProvider>
);

// Admin Portal Routes
const AdminRoutes = () => (
  <AdminAuthProvider>
    <Routes>
      <Route path="login" element={<AdminLogin />} />
      <Route
        path="/"
        element={
          <AdminProtectedRoute>
            <AdminLayout><AdminDashboard /></AdminLayout>
          </AdminProtectedRoute>
        }
      />
      <Route
        path="dashboard"
        element={
          <AdminProtectedRoute>
            <AdminLayout><AdminDashboard /></AdminLayout>
          </AdminProtectedRoute>
        }
      />
      <Route
        path="clinics"
        element={
          <AdminProtectedRoute>
            <AdminLayout><AdminClinics /></AdminLayout>
          </AdminProtectedRoute>
        }
      />
      <Route
        path="doctors"
        element={
          <AdminProtectedRoute>
            <AdminLayout><AdminDoctors /></AdminLayout>
          </AdminProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  </AdminAuthProvider>
);

// Main App
const App = () => (
  <Routes>
    {/* Chatbot Home (Main Page) */}
    <Route path="/" element={<Home />} />

    {/* Doctor Portal */}
    <Route path="/doctor/*" element={<DoctorRoutes />} />

    {/* Admin Portal */}
    <Route path="/admin/*" element={<AdminRoutes />} />

    {/* Fallback */}
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default App;
