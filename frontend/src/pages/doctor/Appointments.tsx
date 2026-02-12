import { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Snackbar,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  Stack,
  Divider,
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Event as EventIcon,
  Cancel as CancelIcon,
  CheckCircle as CheckCircleIcon,
  Visibility as VisibilityIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { portalApi } from '../../services/api';
import type { AppointmentItem } from '../../types';

const statusColors: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  booked: 'success',
  confirmed: 'success',
  pending: 'warning',
  rescheduled: 'info',
  cancelled: 'error',
  completed: 'default',
};

type StatusFilter = 'all' | 'booked' | 'rescheduled' | 'cancelled' | 'completed';

const Appointments = () => {
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  // Menu state
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedAppointment, setSelectedAppointment] = useState<AppointmentItem | null>(null);

  // Dialog states
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [rescheduleDialogOpen, setRescheduleDialogOpen] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [completeDialogOpen, setCompleteDialogOpen] = useState(false);

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

  const fetchAppointments = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (statusFilter !== 'all') {
        params.status_filter = statusFilter;
      }
      const response = await portalApi.get('/dashboard/appointments', { params });
      setAppointments(response.data.appointments || response.data || []);
    } catch (error) {
      console.error('Failed to fetch appointments:', error);
      setSnackbar({ open: true, message: 'Failed to fetch appointments', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchAppointments();
  }, [fetchAppointments]);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, appointment: AppointmentItem) => {
    setAnchorEl(event.currentTarget);
    setSelectedAppointment(appointment);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleViewDetails = () => {
    setViewDialogOpen(true);
    handleMenuClose();
  };

  const handleOpenReschedule = () => {
    if (selectedAppointment) {
      setRescheduleDate(selectedAppointment.date);
      setRescheduleStartTime(selectedAppointment.start_time);
      setRescheduleEndTime(selectedAppointment.end_time);
      setRescheduleReason('');
      setRescheduleDialogOpen(true);
    }
    handleMenuClose();
  };

  const handleOpenCancel = () => {
    setCancelReason('');
    setCancelDialogOpen(true);
    handleMenuClose();
  };

  const handleOpenComplete = () => {
    setCompleteNotes('');
    setCompleteDialogOpen(true);
    handleMenuClose();
  };

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
      fetchAppointments();
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
      fetchAppointments();
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
      fetchAppointments();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const message = err.response?.data?.detail || 'Failed to complete appointment';
      setSnackbar({ open: true, message, severity: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  const canReschedule = (status: string) => {
    const s = status.toLowerCase();
    return s === 'booked' || s === 'confirmed' || s === 'rescheduled';
  };

  const canCancel = (status: string) => {
    const s = status.toLowerCase();
    return s === 'booked' || s === 'confirmed' || s === 'rescheduled';
  };

  const canComplete = (status: string) => {
    const s = status.toLowerCase();
    return s === 'booked' || s === 'confirmed' || s === 'rescheduled';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Appointments
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your scheduled appointments
          </Typography>
        </Box>
        <FormControl sx={{ minWidth: 150 }} size="small">
          <InputLabel>Filter Status</InputLabel>
          <Select
            value={statusFilter}
            label="Filter Status"
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="booked">Booked</MenuItem>
            <MenuItem value="rescheduled">Rescheduled</MenuItem>
            <MenuItem value="cancelled">Cancelled</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Card sx={{ borderRadius: 3, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: '#f8fafc' }}>
                <TableCell sx={{ fontWeight: 600 }}>Patient</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Time</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {appointments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No appointments found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                appointments.map((apt) => (
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
                        <Tooltip title="View Details">
                          <IconButton
                            size="small"
                            onClick={() => { setSelectedAppointment(apt); setViewDialogOpen(true); }}
                          >
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {canReschedule(apt.status) && (
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
                        )}
                        {canComplete(apt.status) && (
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
                        )}
                        {canCancel(apt.status) && (
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
                        )}
                        <IconButton
                          size="small"
                          onClick={(e) => handleMenuOpen(e, apt)}
                        >
                          <MoreVertIcon fontSize="small" />
                        </IconButton>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleViewDetails}>
          <VisibilityIcon fontSize="small" sx={{ mr: 1 }} /> View Details
        </MenuItem>
        {selectedAppointment && canReschedule(selectedAppointment.status) && (
          <MenuItem onClick={handleOpenReschedule}>
            <EventIcon fontSize="small" sx={{ mr: 1 }} /> Reschedule
          </MenuItem>
        )}
        {selectedAppointment && canComplete(selectedAppointment.status) && (
          <MenuItem onClick={handleOpenComplete}>
            <CheckCircleIcon fontSize="small" sx={{ mr: 1 }} /> Mark Complete
          </MenuItem>
        )}
        {selectedAppointment && canCancel(selectedAppointment.status) && (
          <MenuItem onClick={handleOpenCancel} sx={{ color: 'error.main' }}>
            <CancelIcon fontSize="small" sx={{ mr: 1 }} /> Cancel Appointment
          </MenuItem>
        )}
      </Menu>

      {/* View Details Dialog */}
      <Dialog open={viewDialogOpen} onClose={() => setViewDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Appointment Details</DialogTitle>
        <DialogContent dividers>
          {selectedAppointment && (
            <Stack spacing={2}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">Patient</Typography>
                <Typography variant="body1" fontWeight={500}>{selectedAppointment.patient.name}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">Contact</Typography>
                <Typography variant="body1">
                  {selectedAppointment.patient.mobile_number || selectedAppointment.patient.email || 'N/A'}
                </Typography>
              </Box>
              <Divider />
              <Box>
                <Typography variant="subtitle2" color="text.secondary">Date</Typography>
                <Typography variant="body1">{selectedAppointment.date}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">Time</Typography>
                <Typography variant="body1">
                  {selectedAppointment.start_time} - {selectedAppointment.end_time}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">Timezone</Typography>
                <Typography variant="body1">{selectedAppointment.timezone}</Typography>
              </Box>
              <Divider />
              <Stack direction="row" spacing={4}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Status</Typography>
                  <Chip
                    label={selectedAppointment.status}
                    color={statusColors[selectedAppointment.status.toLowerCase()] || 'default'}
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Calendar Sync</Typography>
                  <Chip
                    label={selectedAppointment.calendar_sync_status || 'N/A'}
                    color={
                      selectedAppointment.calendar_sync_status === 'SYNCED' ? 'success' :
                      selectedAppointment.calendar_sync_status === 'FAILED' ? 'error' :
                      selectedAppointment.calendar_sync_status === 'PENDING' ? 'warning' : 'default'
                    }
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </Box>
              </Stack>
              {selectedAppointment.source && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Booking Source</Typography>
                  <Typography variant="body1">{selectedAppointment.source.replace(/_/g, ' ')}</Typography>
                </Box>
              )}
              {selectedAppointment.notes && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Notes</Typography>
                  <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{selectedAppointment.notes}</Typography>
                </Box>
              )}
              {selectedAppointment.created_at && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Created At</Typography>
                  <Typography variant="body1">
                    {new Date(selectedAppointment.created_at).toLocaleString()}
                  </Typography>
                </Box>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

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

export default Appointments;
