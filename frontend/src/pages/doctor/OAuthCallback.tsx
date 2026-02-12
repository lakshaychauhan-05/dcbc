import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import { useDoctorAuth } from '../../contexts/DoctorAuthContext';

const OAuthCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setToken } = useDoctorAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get('token');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setError(decodeURIComponent(errorParam));
      setTimeout(() => navigate('/doctor/login'), 3000);
      return;
    }

    if (token) {
      setToken(token);
      navigate('/doctor/dashboard');
    } else {
      setError('No authentication token received');
      setTimeout(() => navigate('/doctor/login'), 3000);
    }
  }, [searchParams, setToken, navigate]);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: '#f5f6fa',
      }}
    >
      {error ? (
        <Alert severity="error" sx={{ maxWidth: 400 }}>
          {error}
          <Typography variant="body2" sx={{ mt: 1 }}>
            Redirecting to login...
          </Typography>
        </Alert>
      ) : (
        <>
          <CircularProgress size={48} />
          <Typography variant="h6" sx={{ mt: 3 }}>
            Completing sign in...
          </Typography>
        </>
      )}
    </Box>
  );
};

export default OAuthCallback;
