import { AppBar, Avatar, Box, Button, Toolbar, Typography } from "@mui/material";
import { useAuth } from "../hooks/useAuth";

const TopBar = () => {
  const { profile, logout } = useAuth();
  return (
    <AppBar position="static" elevation={0} sx={{ bgcolor: "white", color: "#0f172a", borderBottom: "1px solid #e2e8f0" }}>
      <Toolbar sx={{ display: "flex", justifyContent: "space-between" }}>
        <Typography variant="h6" fontWeight={700}>
          {profile ? `Welcome, Dr. ${profile.name.split(" ")[0] || profile.name}` : "Doctor Portal"}
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          {profile && (
            <>
              <Box textAlign="right">
                <Typography variant="body1" fontWeight={600}>
                  {profile.name}
                </Typography>
                <Typography variant="body2" color="#64748b">
                  {profile.specialization}
                </Typography>
              </Box>
              <Avatar sx={{ bgcolor: "#0ea5e9" }}>{profile.name.charAt(0).toUpperCase()}</Avatar>
              <Button variant="outlined" color="inherit" size="small" onClick={logout}>
                Sign out
              </Button>
            </>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default TopBar;
