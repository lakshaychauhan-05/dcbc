import { Box, Typography, Avatar, IconButton, Menu, MenuItem } from '@mui/material';
import { AccountCircle, ExitToApp } from '@mui/icons-material';
import { useState } from 'react';
import { useDoctorAuth } from '../../contexts/DoctorAuthContext';

const TopBar = () => {
  const { profile, logout } = useDoctorAuth();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleClose();
    logout();
  };

  return (
    <Box
      sx={{
        height: 64,
        bgcolor: 'white',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 3,
      }}
    >
      <Typography variant="h6" fontWeight={600} color="text.primary">
        Welcome, Dr. {profile?.name?.split(' ')[0] || 'Doctor'}
      </Typography>

      <Box display="flex" alignItems="center" gap={2}>
        <Typography variant="body2" color="text.secondary">
          {profile?.specialization}
        </Typography>
        <IconButton onClick={handleMenu}>
          <Avatar sx={{ bgcolor: '#3b82f6', width: 36, height: 36 }}>
            {profile?.name?.charAt(0) || <AccountCircle />}
          </Avatar>
        </IconButton>
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        >
          <MenuItem onClick={handleLogout}>
            <ExitToApp sx={{ mr: 1 }} fontSize="small" />
            Logout
          </MenuItem>
        </Menu>
      </Box>
    </Box>
  );
};

export default TopBar;
