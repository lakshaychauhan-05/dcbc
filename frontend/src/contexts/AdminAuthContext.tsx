import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { adminApi } from '../services/api';

interface AdminAuthContextValue {
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AdminAuthContext = createContext<AdminAuthContextValue | undefined>(undefined);

export const AdminAuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('admin_token'));
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (token) {
      localStorage.setItem('admin_token', token);
    } else {
      localStorage.removeItem('admin_token');
    }
  }, [token]);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const resp = await adminApi.post('/login', { email, password });
      setToken(resp.data.access_token);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    window.location.href = '/admin/login';
  };

  return (
    <AdminAuthContext.Provider value={{ token, loading, login, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
};

export const useAdminAuth = (): AdminAuthContextValue => {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) {
    throw new Error('useAdminAuth must be used within AdminAuthProvider');
  }
  return ctx;
};
