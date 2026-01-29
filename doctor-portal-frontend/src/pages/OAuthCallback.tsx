import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CircularProgress, Box, Typography } from "@mui/material";
import { useAuth } from "../hooks/useAuth";

const OAuthCallback = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { setToken } = useAuth();

  useEffect(() => {
    const token = params.get("token");
    if (token) {
      setToken(token);
      navigate("/dashboard", { replace: true });
    } else {
      navigate("/login", { replace: true });
    }
  }, [navigate, params, setToken]);

  return (
    <Box minHeight="100vh" display="flex" flexDirection="column" alignItems="center" justifyContent="center">
      <CircularProgress />
      <Typography sx={{ mt: 2 }}>Finalizing sign-in...</Typography>
    </Box>
  );
};

export default OAuthCallback;
