import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  CircularProgress,
  Divider,
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { portalApi } from '../../services/api';
import type { PatientDetail as PatientDetailType } from '../../types';

const PatientDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<PatientDetailType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPatient = async () => {
      try {
        const response = await portalApi.get(`/dashboard/patients/${id}`);
        setPatient(response.data);
      } catch (error) {
        console.error('Failed to fetch patient:', error);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchPatient();
    }
  }, [id]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!patient) {
    return (
      <Box>
        <Typography>Patient not found</Typography>
        <Button onClick={() => navigate('/doctor/patients')}>Back to Patients</Button>
      </Box>
    );
  }

  return (
    <Box>
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate('/doctor/patients')}
        sx={{ mb: 3 }}
      >
        Back to Patients
      </Button>

      <Typography variant="h4" fontWeight={700} gutterBottom>
        Patient Details
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ borderRadius: 3, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Basic Information
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Box display="grid" gap={2}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Name
                  </Typography>
                  <Typography fontWeight={500}>{patient.name}</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Phone
                  </Typography>
                  <Typography>{patient.mobile_number || '-'}</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Email
                  </Typography>
                  <Typography>{patient.email || '-'}</Typography>
                </Box>
                {patient.gender && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Gender
                    </Typography>
                    <Typography>{patient.gender}</Typography>
                  </Box>
                )}
                {patient.date_of_birth && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Date of Birth
                    </Typography>
                    <Typography>{patient.date_of_birth}</Typography>
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ borderRadius: 3, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Medical History
              </Typography>
              <Divider sx={{ mb: 2 }} />
              {patient.history && patient.history.length > 0 ? (
                patient.history.map((item, index) => (
                  <Box key={item.id || index} sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(item.created_at).toLocaleDateString()}
                    </Typography>
                    {item.symptoms && (
                      <Typography variant="body2">Symptoms: {item.symptoms}</Typography>
                    )}
                    {item.notes && <Typography variant="body2">Notes: {item.notes}</Typography>}
                  </Box>
                ))
              ) : (
                <Typography color="text.secondary">No medical history available</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default PatientDetail;
