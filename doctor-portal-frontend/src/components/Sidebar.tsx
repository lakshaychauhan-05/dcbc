import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import EventNoteIcon from "@mui/icons-material/EventNote";
import PeopleIcon from "@mui/icons-material/People";
import SettingsIcon from "@mui/icons-material/Settings";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import { useLocation, useNavigate } from "react-router-dom";

const navItems = [
  { to: "/dashboard", label: "Overview", icon: <DashboardIcon /> },
  { to: "/appointments", label: "Appointments", icon: <EventNoteIcon /> },
  { to: "/patients", label: "Patients", icon: <PeopleIcon /> },
  { to: "/settings", label: "Settings", icon: <SettingsIcon /> },
];

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  return (
    <Box
      width={260}
      sx={{
        background: "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)",
        color: "white",
        display: "flex",
        flexDirection: "column",
        boxShadow: "4px 0 20px rgba(0, 0, 0, 0.15)",
        position: "relative",
        minHeight: "100vh",
        "&::after": {
          content: '""',
          position: "absolute",
          top: 0,
          right: 0,
          bottom: 0,
          width: 1,
          background: "linear-gradient(180deg, rgba(59, 130, 246, 0.3) 0%, transparent 100%)",
        },
      }}
    >
      {/* Logo Section */}
      <Box
        px={3}
        py={3}
        display="flex"
        alignItems="center"
        gap={2}
        sx={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          cursor: "pointer",
        }}
        onClick={() => handleNavigation("/dashboard")}
      >
        <Box
          sx={{
            width: 44,
            height: 44,
            borderRadius: 2,
            background: "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 12px rgba(59, 130, 246, 0.3)",
          }}
        >
          <LocalHospitalIcon sx={{ fontSize: 24, color: "white" }} />
        </Box>
        <Box>
          <Typography variant="h6" fontWeight={700} sx={{ lineHeight: 1.2 }}>
            Doctor Portal
          </Typography>
          <Typography variant="caption" sx={{ color: "#94a3b8" }}>
            Healthcare Management
          </Typography>
        </Box>
      </Box>

      {/* Navigation */}
      <List sx={{ flex: 1, py: 2, px: 1.5 }}>
        {navItems.map((item) => {
          const active = location.pathname === item.to ||
            (item.to !== "/dashboard" && location.pathname.startsWith(item.to));
          return (
            <ListItemButton
              key={item.to}
              onClick={() => handleNavigation(item.to)}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                py: 1.2,
                px: 2,
                color: active ? "#ffffff" : "#94a3b8",
                background: active
                  ? "linear-gradient(90deg, rgba(59, 130, 246, 0.2) 0%, rgba(59, 130, 246, 0.05) 100%)"
                  : "transparent",
                borderLeft: active ? "3px solid #3b82f6" : "3px solid transparent",
                transition: "all 0.2s ease",
                "&:hover": {
                  bgcolor: "rgba(59, 130, 246, 0.1)",
                  color: "#ffffff",
                  "& .MuiListItemIcon-root": {
                    color: "#3b82f6",
                  },
                },
              }}
            >
              <ListItemIcon
                sx={{
                  color: active ? "#3b82f6" : "#64748b",
                  minWidth: 40,
                  transition: "color 0.2s ease",
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontWeight: active ? 600 : 500,
                  fontSize: "0.95rem",
                }}
              />
            </ListItemButton>
          );
        })}
      </List>

      {/* Footer */}
      <Box px={3} py={2} sx={{ borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
        <Typography variant="caption" sx={{ color: "#64748b" }}>
          Calendar Booking System
        </Typography>
      </Box>
    </Box>
  );
};

export default Sidebar;
