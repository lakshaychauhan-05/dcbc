import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { DoctorProfile } from "../types";

type AuthContextValue = {
  token: string | null;
  profile: DoctorProfile | null;
  setToken: (token: string | null) => void;
  loading: boolean;
  refreshProfile: () => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setTokenState] = useState<string | null>(localStorage.getItem("portal_token"));
  const [profile, setProfile] = useState<DoctorProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(!!token);

  const setToken = (newToken: string | null) => {
    setTokenState(newToken);
    if (newToken) {
      localStorage.setItem("portal_token", newToken);
    } else {
      localStorage.removeItem("portal_token");
    }
  };

  const refreshProfile = async () => {
    if (!token) return;
    try {
      const res = await api.get("/dashboard/me");
      setProfile(res.data);
    } catch (err) {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = useCallback(() => {
    // Clear all auth data
    localStorage.removeItem("portal_token");
    setTokenState(null);
    setProfile(null);
    // Force redirect to login page
    window.location.href = "/login";
  }, []);

  useEffect(() => {
    if (token) {
      refreshProfile();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <AuthContext.Provider value={{ token, profile, setToken, loading, refreshProfile, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
};
