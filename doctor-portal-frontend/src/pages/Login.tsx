import { useState, FormEvent } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  Typography,
  TextField,
  Divider,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton,
} from "@mui/material";
import GoogleIcon from "@mui/icons-material/Google";
import EmailIcon from "@mui/icons-material/Email";
import LockIcon from "@mui/icons-material/Lock";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import api from "../services/api";

const Login = () => {
  const navigate = useNavigate();
  const { setToken } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = async () => {
    setError(null);
    try {
      const res = await api.get("/auth/oauth/google/start");
      const url = res.data.url;
      window.location.href = url;
    } catch {
      setError("Unable to start Google login. Please check configuration or use email/password.");
    }
  };

  const handleEmailLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await api.post("/auth/login", { email, password });
      const token = res.data.access_token;
      setToken(token);
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string }; status?: number }; message?: string; code?: string };
      if (axiosError.code === "ERR_NETWORK" || !axiosError.response) {
        // CORS or network error - request didn't reach the server
        setError("Unable to connect to server. Please ensure the backend is running and try again.");
      } else {
        const detail = axiosError.response?.data?.detail;
        setError(detail ?? "Invalid email or password");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      minHeight="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      sx={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)",
        position: "relative",
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "radial-gradient(circle at 30% 20%, rgba(59, 130, 246, 0.1) 0%, transparent 50%)",
          pointerEvents: "none",
        },
      }}
    >
      <Card
        sx={{
          maxWidth: 440,
          width: "100%",
          mx: 2,
          borderRadius: 3,
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
          bgcolor: "#ffffff",
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={3} alignItems="center">
            {/* Logo */}
            <Box
              sx={{
                width: 64,
                height: 64,
                borderRadius: 2,
                background: "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 10px 30px rgba(59, 130, 246, 0.3)",
              }}
            >
              <LocalHospitalIcon sx={{ fontSize: 36, color: "white" }} />
            </Box>

            {/* Header */}
            <Box textAlign="center">
              <Typography variant="h4" fontWeight={700} color="#0f172a" gutterBottom>
                Doctor Portal
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Sign in to manage your appointments and patients
              </Typography>
            </Box>

            {/* Error Alert */}
            {error && (
              <Alert severity="error" sx={{ width: "100%" }}>
                {error}
              </Alert>
            )}

            {/* Email/Password Form */}
            <Box component="form" onSubmit={handleEmailLogin} width="100%">
              <Stack spacing={2.5}>
                <TextField
                  fullWidth
                  label="Email Address"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  autoFocus
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <EmailIcon sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      borderRadius: 2,
                      "&:hover fieldset": { borderColor: "#3b82f6" },
                      "&.Mui-focused fieldset": { borderColor: "#3b82f6" },
                    },
                  }}
                />
                <TextField
                  fullWidth
                  label="Password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockIcon sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                          size="small"
                        >
                          {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      borderRadius: 2,
                      "&:hover fieldset": { borderColor: "#3b82f6" },
                      "&.Mui-focused fieldset": { borderColor: "#3b82f6" },
                    },
                  }}
                />
                <Button
                  type="submit"
                  variant="contained"
                  fullWidth
                  disabled={loading}
                  sx={{
                    py: 1.5,
                    borderRadius: 2,
                    textTransform: "none",
                    fontSize: "1rem",
                    fontWeight: 600,
                    background: "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
                    boxShadow: "0 4px 14px rgba(59, 130, 246, 0.4)",
                    "&:hover": {
                      background: "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)",
                      boxShadow: "0 6px 20px rgba(59, 130, 246, 0.5)",
                    },
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} sx={{ color: "white" }} />
                  ) : (
                    "Sign In"
                  )}
                </Button>
              </Stack>
            </Box>

            {/* Divider */}
            <Divider sx={{ width: "100%", my: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ px: 2 }}>
                or continue with
              </Typography>
            </Divider>

            {/* Google OAuth */}
            <Button
              onClick={handleGoogleLogin}
              startIcon={<GoogleIcon />}
              variant="outlined"
              fullWidth
              sx={{
                py: 1.5,
                borderRadius: 2,
                textTransform: "none",
                fontSize: "1rem",
                fontWeight: 500,
                borderColor: "#e2e8f0",
                color: "#334155",
                "&:hover": {
                  borderColor: "#3b82f6",
                  bgcolor: "rgba(59, 130, 246, 0.04)",
                },
              }}
            >
              Continue with Google
            </Button>

            {/* Footer */}
            <Typography variant="caption" color="text.secondary" textAlign="center" sx={{ mt: 2 }}>
              Only registered doctors can access this portal.
              <br />
              Contact your clinic administrator if you need access.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Login;
