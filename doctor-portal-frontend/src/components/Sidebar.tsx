import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import EventNoteIcon from "@mui/icons-material/EventNote";
import PeopleIcon from "@mui/icons-material/People";
import { NavLink, useLocation } from "react-router-dom";

const navItems = [
  { to: "/dashboard", label: "Overview", icon: <DashboardIcon fontSize="small" /> },
  { to: "/appointments", label: "Appointments", icon: <EventNoteIcon fontSize="small" /> },
  { to: "/patients", label: "Patients", icon: <PeopleIcon fontSize="small" /> },
];

const Sidebar = () => {
  const location = useLocation();
  return (
    <Box
      width={240}
      bgcolor="#0f172a"
      color="white"
      display="flex"
      flexDirection="column"
      borderRight="1px solid #1f2937"
    >
      <Box px={2} py={3} borderBottom="1px solid #1f2937">
        <Typography variant="h6" fontWeight={700}>
          Doctor Portal
        </Typography>
        <Typography variant="body2" color="#cbd5e1">
          Schedule & Patients
        </Typography>
      </Box>
      <List sx={{ flex: 1 }}>
        {navItems.map((item) => {
          const active = location.pathname.startsWith(item.to);
          return (
            <ListItemButton
              key={item.to}
              component={NavLink}
              to={item.to}
              selected={active}
              sx={{
                color: active ? "#fff" : "#cbd5e1",
                "&.Mui-selected": { bgcolor: "#1f2937" },
                "&:hover": { bgcolor: "#1f2937" },
              }}
            >
              <ListItemIcon sx={{ color: active ? "#22d3ee" : "#cbd5e1" }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );
};

export default Sidebar;
