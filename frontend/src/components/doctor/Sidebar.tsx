import { NavLink } from 'react-router-dom';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Event as EventIcon,
  People as PeopleIcon,
  Settings as SettingsIcon,
  Home as HomeIcon,
} from '@mui/icons-material';

const navItems = [
  { path: '/doctor/dashboard', label: 'Dashboard', icon: DashboardIcon },
  { path: '/doctor/appointments', label: 'Appointments', icon: EventIcon },
  { path: '/doctor/patients', label: 'Patients', icon: PeopleIcon },
  { path: '/doctor/settings', label: 'Settings', icon: SettingsIcon },
];

const Sidebar = () => {
  return (
    <Box
      sx={{
        width: 260,
        bgcolor: '#1a1f2e',
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
      }}
    >
      {/* Logo */}
      <Box sx={{ p: 3, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <Typography variant="h6" fontWeight={700} sx={{ color: '#3b82f6' }}>
          Doctor Portal
        </Typography>
      </Box>

      {/* Navigation */}
      <List sx={{ flex: 1, px: 2, py: 2 }}>
        {navItems.map((item) => (
          <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              component={NavLink}
              to={item.path}
              sx={{
                borderRadius: 2,
                color: 'rgba(255,255,255,0.7)',
                '&:hover': {
                  bgcolor: 'rgba(59, 130, 246, 0.1)',
                  color: 'white',
                },
                '&.active': {
                  bgcolor: '#3b82f6',
                  color: 'white',
                  '&:hover': {
                    bgcolor: '#2563eb',
                  },
                },
              }}
            >
              <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>
                <item.icon />
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      {/* Back to Home */}
      <Box sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <ListItemButton
          component={NavLink}
          to="/"
          sx={{
            borderRadius: 2,
            color: 'rgba(255,255,255,0.7)',
            '&:hover': {
              bgcolor: 'rgba(255,255,255,0.1)',
              color: 'white',
            },
          }}
        >
          <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>
            <HomeIcon />
          </ListItemIcon>
          <ListItemText primary="Back to Home" />
        </ListItemButton>
      </Box>
    </Box>
  );
};

export default Sidebar;
