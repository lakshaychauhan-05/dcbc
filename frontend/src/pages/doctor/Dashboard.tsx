import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Stack,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  Event as EventIcon,
  People as PeopleIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Cancel as CancelIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';
import { portalApi } from '../../services/api';
import type { AppointmentItem, DoctorProfile } from '../../types';

interface OverviewData {
  doctor: DoctorProfile;
  upcoming_appointments: AppointmentItem[];
}

const statusColors: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  booked: 'success',
  confirmed: 'success',
  pending: 'warning',
  rescheduled: 'info',
  cancelled: 'error',
  completed: 'default',
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);

  // Dialog states
  const [rescheduleDialogOpen, setRescheduleDialogOpen] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [completeDialogOpen, setCompleteDialogOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState<AppointmentItem | null>(null);

  // Form states
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleStartTime, setRescheduleStartTime] = useState('');
  const [rescheduleEndTime, setRescheduleEndTime] = useState('');
  const [rescheduleReason, setRescheduleReason] = useState('');
  const [cancelReason, setCancelReason] = useState('');
  const [completeNotes, setCompleteNotes] = useState('');

  // Loading and notification states
  const [actionLoading, setActionLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const fetchOverview = useCallback(async () => {
    try {
      const response = await portalApi.get('/dashboard/overview');
      setOverview(response.data);
    } catch (error) {
      console.error('Failed to fetch overview:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const handleReschedule = async () => {
    if (!selectedAppointment) return;

    if (!rescheduleDate || !rescheduleStartTime || !rescheduleEndTime) {
      setSnackbar({ open: true, message: 'Please fill in all required fields', severity: 'error' });
      return;
    }

    setActionLoading(true);
    try {
      await portalApi.put(`/dashboard/appointments/${selectedAppointment.id}/reschedule`, {
        new_date: rescheduleDate,
        new_start_time: rescheduleStartTime,
        new_end_time: rescheduleEndTime,
        reason: rescheduleReason || undefined,
      });
      setSnackbar({ open: true, message: 'Appointment rescheduled successfully. SMS notifications sent.', severity: 'success' });
      setRescheduleDialogOpen(false);
      fetchOverview();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Failed to reschedule appointment';
      setSnackbar({ open: true, message, severity: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!selectedAppointment) return;

    setActionLoading(true);
    try {
      await portalApi.post(`/dashboard/appointments/${selectedAppointment.id}/cancel`, {
        reason: cancelReason || undefined,
      });
      setSnackbar({ open: true, message: 'Appointment cancelled successfully. SMS notifications sent.', severity: 'success' });
      setCancelDialogOpen(false);
      fetchOverview();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Failed to cancel appointment';
      setSnackbar({ open: true, message, severity: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!selectedAppointment) return;

    setActionLoading(true);
    try {
      await portalApi.post(`/dashboard/appointments/${selectedAppointment.id}/complete`, {
        notes: completeNotes || undefined,
      });
      setSnackbar({ open: true, message: 'Appointment marked as completed', severity: 'success' });
      setCompleteDialogOpen(false);
      fetchOverview();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Failed to complete appointment';
      setSnackbar({ open: true, message, severity: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const upcomingAppointments = overview?.upcoming_appointments || [];
  const todayCount = upcomingAppointments.filter(apt => {
    const today = new Date().toISOString().split('T')[0];
    return apt.date === today;
  }).length;

  const statCards = [
    {
      title: "Today's Appointments",
      value: todayCount,
      icon: EventIcon,
      color: '#3b82f6',
    },
    {
      title: 'Upcoming',
      value: upcomingAppointments.length,
      icon: ScheduleIcon,
      color: '#10b981',
    },
    {
      title: 'Specialization',
      value: overview?.doctor?.specialization || 'N/A',
      icon: PeopleIcon,
      color: '#8b5cf6',
      isText: true,
    },
    {
      title: 'Experience',
      value: `${overview?.doctor?.experience_years || 0} years`,
      icon: CheckCircleIcon,
      color: '#f59e0b',
      isText: true,
    },
  ];

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        Welcome back, Dr. {overview?.doctor?.name?.split(' ')[0] || 'Doctor'}
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={4}>
        Here's your practice overview
      </Typography>

      <Grid container spacing={3} mb={4}>
        {statCards.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card
              sx={{
                borderRadius: 3,
                boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                },
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {stat.title}
                    </Typography>
                    <Typography variant={stat.isText ? 'h6' : 'h3'} fontWeight={700}>
                      {stat.value}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      width: 56,
                      height: 56,
                      borderRadius: 2,
                      bgcolor: `${stat.color}15`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <stat.icon sx={{ fontSize: 28, color: stat.color }} />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Upcoming Appointments */}
      <Card sx={{ borderRadius: 3, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
        <CardContent sx={{ p: 0 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" p={3} pb={2}>
            <Typography variant="h6" fontWeight={600}>
              Upcoming Appointments
            </Typography>
            <Button
              endIcon={<ArrowForwardIcon />}
              onClick={() => navigate('/doctor/appointments')}
            >
              View All
            </Button>
          </Box>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#f8fafc' }}>
                  <TableCell sx={{ fontWeight: 600 }}>Patient</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Time</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Quick Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {upcomingAppointments.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                      <Typography color="text.secondary">No upcoming appointments</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  upcomingAppointments.slice(0, 5).map((apt) => (
                    <TableRow key={apt.id} hover>
                      <TableCell>
                        <Typography fontWeight={500}>{apt.patient.name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {apt.patient.mobile_number || apt.patient.email}
                        </Typography>
                      </TableCell>
                      <TableCell>{apt.date}</TableCell>
                      <TableCell>
                        {apt.start_time} - {apt.end_time}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={apt.status}
                          color={statusColors[apt.status.toLowerCase()] || 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Tooltip title="Reschedule">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => {
                                setSelectedAppointment(apt);
                                setRescheduleDate(apt.date);
                                setRescheduleStartTime(apt.start_time);
                                setRescheduleEndTime(apt.end_time);
                                setRescheduleReason('');
                                setRescheduleDialogOpen(true);
                              }}
                            >
                              <ScheduleIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Mark Complete">
                            <IconButton
                              size="small"
                              color="success"
                              onClick={() => {
                                setSelectedAppointment(apt);
                                setCompleteNotes('');
                                setCompleteDialogOpen(true);
                              }}
                            >
                              <CheckCircleIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Cancel">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => {
                                setSelectedAppointment(apt);
                                setCancelReason('');
                                setCancelDialogOpen(true);
                              }}
                            >
                              <CancelIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Reschedule Dialog */}
      <Dialog open={rescheduleDialogOpen} onClose={() => setRescheduleDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Reschedule Appointment</DialogTitle>
        <DialogContent dividers>
          {selectedAppointment && (
            <Stack spacing={3} sx={{ mt: 1 }}>
              <Alert severity="info">
                Rescheduling will update the calendar and send SMS notifications to both you and the patient.
              </Alert>
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Current: {selectedAppointment.date} at {selectedAppointment.start_time} - {selectedAppointment.end_time}
                </Typography>
              </Box>
              <TextField
                label="New Date"
                type="date"
                value={rescheduleDate}
                onChange={(e) => setRescheduleDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
                fullWidth
                required
              />
              <Stack direction="row" spacing={2}>
                <TextField
                  label="Start Time"
                  type="time"
                  value={rescheduleStartTime}
                  onChange={(e) => setRescheduleStartTime(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  required
                />
                <TextField
                  label="End Time"
                  type="time"
                  value={rescheduleEndTime}
                  onChange={(e) => setRescheduleEndTime(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  required
                />
              </Stack>
              <TextField
                label="Reason (optional)"
                value={rescheduleReason}
                onChange={(e) => setRescheduleReason(e.target.value)}
                multiline
                rows={2}
                fullWidth
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRescheduleDialogOpen(false)} disabled={actionLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleReschedule}
            variant="contained"
            color="primary"
            disabled={actionLoading}
          >
            {actionLoading ? <CircularProgress size={24} /> : 'Reschedule'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Cancel Dialog */}
      <Dialog open={cancelDialogOpen} onClose={() => setCancelDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Cancel Appointment</DialogTitle>
        <DialogContent dividers>
          {selectedAppointment && (
            <Stack spacing={3} sx={{ mt: 1 }}>
              <Alert severity="warning">
                Cancelling will remove this appointment from the calendar and send SMS notifications to both you and the patient.
              </Alert>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">Appointment</Typography>
                <Typography variant="body1">
                  {selectedAppointment.patient.name} on {selectedAppointment.date} at {selectedAppointment.start_time}
                </Typography>
              </Box>
              <TextField
                label="Cancellation Reason (optional)"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                multiline
                rows={3}
                fullWidth
                placeholder="e.g., Doctor unavailable, Patient requested cancellation"
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelDialogOpen(false)} disabled={actionLoading}>
            Keep Appointment
          </Button>
          <Button
            onClick={handleCancel}
            variant="contained"
            color="error"
            disabled={actionLoading}
          >
            {actionLoading ? <CircularProgress size={24} /> : 'Cancel Appointment'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Complete Dialog */}
      <Dialog open={completeDialogOpen} onClose={() => setCompleteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Mark Appointment as Completed</DialogTitle>
        <DialogContent dividers>
          {selectedAppointment && (
            <Stack spacing={3} sx={{ mt: 1 }}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">Appointment</Typography>
                <Typography variant="body1">
                  {selectedAppointment.patient.name} on {selectedAppointment.date} at {selectedAppointment.start_time}
                </Typography>
              </Box>
              <TextField
                label="Notes (optional)"
                value={completeNotes}
                onChange={(e) => setCompleteNotes(e.target.value)}
                multiline
                rows={3}
                fullWidth
                placeholder="Add any notes about the appointment..."
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCompleteDialogOpen(false)} disabled={actionLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleComplete}
            variant="contained"
            color="success"
            disabled={actionLoading}
          >
            {actionLoading ? <CircularProgress size={24} /> : 'Mark Complete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Dashboard;
