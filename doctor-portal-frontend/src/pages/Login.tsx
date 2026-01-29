import { Box, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import GoogleIcon from "@mui/icons-material/Google";
import api from "../services/api";

const Login = () => {
  const handleGoogleLogin = async () => {
    try {
      const res = await api.get("/auth/oauth/google/start");
      const url = res.data.url;
      window.location.href = url;
    } catch (err) {
      alert("Unable to start login. Please check configuration.");
    }
  };

  return (
    <Box minHeight="100vh" display="flex" alignItems="center" justifyContent="center" bgcolor="#0f172a">
      <Card sx={{ maxWidth: 420, width: "100%", p: 1 }}>
        <CardContent>
          <Stack spacing={3} alignItems="center">
            <Typography variant="h5" fontWeight={700}>
              Doctor Portal
            </Typography>
            <Typography variant="body1" color="text.secondary" textAlign="center">
              Sign in with your doctor email using Google OAuth.
            </Typography>
            <Button
              onClick={handleGoogleLogin}
              startIcon={<GoogleIcon />}
              variant="contained"
              fullWidth
              sx={{ bgcolor: "#0f172a", "&:hover": { bgcolor: "#111827" }, py: 1.4 }}
            >
              Continue with Google
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Login;
