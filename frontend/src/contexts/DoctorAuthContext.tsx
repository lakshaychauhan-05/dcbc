import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import { portalApi } from '../services/api';
import type { DoctorProfile } from '../types';

interface DoctorAuthContextValue {
  token: string | null;
  profile: DoctorProfile | null;
  setToken: (token: string | null) => void;
  loading: boolean;
  refreshProfile: () => Promise<void>;
  logout: () => void;
}

const DoctorAuthContext = createContext<DoctorAuthContextValue | undefined>(undefined);

export const DoctorAuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setTokenState] = useState<string | null>(localStorage.getItem('portal_token'));
  const [profile, setProfile] = useState<DoctorProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(!!token);

  const setToken = (newToken: string | null) => {
    setTokenState(newToken);
    if (newToken) {
      localStorage.setItem('portal_token', newToken);
    } else {
      localStorage.removeItem('portal_token');
    }
  };

  const refreshProfile = async () => {
    if (!token) return;
    try {
      const res = await portalApi.get('/dashboard/me');
      setProfile(res.data);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = useCallback(() => {
    localStorage.removeItem('portal_token');
    setTokenState(null);
    setProfile(null);
    window.location.href = '/doctor/login';
  }, []);

  useEffect(() => {
    if (token) {
      refreshProfile();
    } else {
      setLoading(false);
    }
  }, [token]);

  return (
    <DoctorAuthContext.Provider value={{ token, profile, setToken, loading, refreshProfile, logout }}>
      {children}
    </DoctorAuthContext.Provider>
  );
};

export const useDoctorAuth = (): DoctorAuthContextValue => {
  const ctx = useContext(DoctorAuthContext);
  if (!ctx) {
    throw new Error('useDoctorAuth must be used within DoctorAuthProvider');
  }
  return ctx;
};
