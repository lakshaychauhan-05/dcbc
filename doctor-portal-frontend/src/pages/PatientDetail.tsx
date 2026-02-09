import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
  Avatar,
  Grid,
  IconButton,
  Tooltip,
  Skeleton,
  Divider,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PhoneIcon from "@mui/icons-material/Phone";
import EmailIcon from "@mui/icons-material/Email";
import CakeIcon from "@mui/icons-material/Cake";
import PersonIcon from "@mui/icons-material/Person";
import HistoryIcon from "@mui/icons-material/History";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import WarningIcon from "@mui/icons-material/Warning";
import NotesIcon from "@mui/icons-material/Notes";
import AddIcon from "@mui/icons-material/Add";
import SmsIcon from "@mui/icons-material/Sms";
import api from "../services/api";
import { PatientDetail as PatientDetailType, PatientHistoryItem } from "../types";

interface AddHistoryForm {
  symptoms: string;
  medical_conditions: string;
  allergies: string;
  notes: string;
}

const PatientDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<PatientDetailType | null>(null);
  const [loading, setLoading] = useState(true);

  // Add History Dialog State
  const [addHistoryOpen, setAddHistoryOpen] = useState(false);
  const [addHistoryLoading, setAddHistoryLoading] = useState(false);
  const [addHistoryForm, setAddHistoryForm] = useState<AddHistoryForm>({
    symptoms: "",
    medical_conditions: "",
    allergies: "",
    notes: "",
  });
  const [alert, setAlert] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const fetchPatient = async () => {
    if (!id) return;
    try {
      const res = await api.get<PatientDetailType>(`/dashboard/patients/${id}`);
      setPatient(res.data);
    } catch {
      setPatient(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatient();
  }, [id]);

  const handleAddHistoryOpen = () => {
    setAddHistoryForm({ symptoms: "", medical_conditions: "", allergies: "", notes: "" });
    setAddHistoryOpen(true);
  };

  const handleAddHistoryClose = () => {
    setAddHistoryOpen(false);
    setAddHistoryForm({ symptoms: "", medical_conditions: "", allergies: "", notes: "" });
  };

  const handleAddHistorySubmit = async () => {
    if (!id) return;
    setAddHistoryLoading(true);
    try {
      const payload = {
        symptoms: addHistoryForm.symptoms || null,
        medical_conditions: addHistoryForm.medical_conditions
          ? addHistoryForm.medical_conditions.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        allergies: addHistoryForm.allergies
          ? addHistoryForm.allergies.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        notes: addHistoryForm.notes || null,
      };
      await api.post<PatientHistoryItem>(`/dashboard/patients/${id}/history`, payload);
      setAlert({ type: "success", message: "Medical history added successfully" });
      handleAddHistoryClose();
      fetchPatient();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setAlert({
        type: "error",
        message: error.response?.data?.detail || "Failed to add medical history",
      });
    } finally {
      setAddHistoryLoading(false);
    }
  };

  if (loading) {
    return (
      <Stack spacing={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <Skeleton variant="circular" width={40} height={40} />
          <Skeleton variant="rectangular" width={200} height={32} sx={{ borderRadius: 2 }} />
        </Box>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 3 }} />
          </Grid>
          <Grid item xs={12} md={8}>
            <Skeleton variant="rectangular" height={400} sx={{ borderRadius: 3 }} />
          </Grid>
        </Grid>
      </Stack>
    );
  }

  if (!patient) {
    return (
      <Stack spacing={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <Tooltip title="Back to Patients">
            <IconButton onClick={() => navigate("/patients")} sx={{ bgcolor: "#f1f5f9" }}>
              <ArrowBackIcon />
            </IconButton>
          </Tooltip>
          <Typography variant="h5" fontWeight={700} color="#0f172a">
            Patient Not Found
          </Typography>
        </Box>
        <Card
          sx={{
            borderRadius: 3,
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.04)",
            border: "1px solid #e2e8f0",
          }}
        >
          <CardContent sx={{ py: 6, textAlign: "center" }}>
            <PersonIcon sx={{ fontSize: 48, color: "#cbd5e1", mb: 2 }} />
            <Typography color="text.secondary">
              The patient you're looking for doesn't exist or you don't have access.
            </Typography>
          </CardContent>
        </Card>
      </Stack>
    );
  }

  return (
    <Stack spacing={3}>
      {/* Alert */}
      {alert && (
        <Alert
          severity={alert.type}
          onClose={() => setAlert(null)}
          sx={{ borderRadius: 2 }}
        >
          {alert.message}
        </Alert>
      )}

      {/* Header */}
      <Box display="flex" alignItems="center" gap={2}>
        <Tooltip title="Back to Patients">
          <IconButton
            onClick={() => navigate("/patients")}
            sx={{
              bgcolor: "#f1f5f9",
              "&:hover": { bgcolor: "#e2e8f0" },
            }}
          >
            <ArrowBackIcon />
          </IconButton>
        </Tooltip>
        <Box>
          <Typography variant="h4" fontWeight={700} color="#0f172a">
            Patient Details
          </Typography>
          <Typography variant="body2" color="text.secondary">
            View patient information and medical history
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Patient Info Card */}
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: "0 4px 20px rgba(0, 0, 0, 0.05)",
              border: "1px solid #e2e8f0",
              height: "100%",
            }}
          >
            <CardContent sx={{ p: 3 }}>
              {/* Avatar and Name */}
              <Box display="flex" flexDirection="column" alignItems="center" textAlign="center" mb={3}>
                <Avatar
                  sx={{
                    width: 100,
                    height: 100,
                    bgcolor: "#e2e8f0",
                    color: "#475569",
                    fontWeight: 700,
                    fontSize: "2rem",
                    mb: 2,
                  }}
                >
                  {patient.name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase()}
                </Avatar>
                <Typography variant="h5" fontWeight={700} color="#0f172a">
                  {patient.name}
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Contact Details */}
              <Typography variant="subtitle2" color="text.secondary" fontWeight={600} mb={2}>
                Contact Information
              </Typography>

              <Stack spacing={2}>
                <Box display="flex" alignItems="center" gap={2}>
                  <Box
                    sx={{
                      width: 40,
                      height: 40,
                      borderRadius: 2,
                      bgcolor: "#f1f5f9",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <PhoneIcon sx={{ fontSize: 20, color: "#64748b" }} />
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Phone
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {patient.mobile_number || "Not provided"}
                    </Typography>
                  </Box>
                </Box>

                <Box display="flex" alignItems="center" gap={2}>
                  <Box
                    sx={{
                      width: 40,
                      height: 40,
                      borderRadius: 2,
                      bgcolor: patient.sms_opt_in !== false ? "#dcfce7" : "#fee2e2",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <SmsIcon sx={{ fontSize: 20, color: patient.sms_opt_in !== false ? "#16a34a" : "#dc2626" }} />
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      SMS Notifications
                    </Typography>
                    <Typography variant="body2" fontWeight={500} color={patient.sms_opt_in !== false ? "#16a34a" : "#dc2626"}>
                      {patient.sms_opt_in !== false ? "Enabled" : "Disabled"}
                    </Typography>
                  </Box>
                </Box>

                <Box display="flex" alignItems="center" gap={2}>
                  <Box
                    sx={{
                      width: 40,
                      height: 40,
                      borderRadius: 2,
                      bgcolor: "#f1f5f9",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <EmailIcon sx={{ fontSize: 20, color: "#64748b" }} />
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Email
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {patient.email || "Not provided"}
                    </Typography>
                  </Box>
                </Box>

                {patient.gender && (
                  <Box display="flex" alignItems="center" gap={2}>
                    <Box
                      sx={{
                        width: 40,
                        height: 40,
                        borderRadius: 2,
                        bgcolor: "#f1f5f9",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <PersonIcon sx={{ fontSize: 20, color: "#64748b" }} />
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Gender
                      </Typography>
                      <Typography variant="body2" fontWeight={500}>
                        {patient.gender}
                      </Typography>
                    </Box>
                  </Box>
                )}

                {patient.date_of_birth && (
                  <Box display="flex" alignItems="center" gap={2}>
                    <Box
                      sx={{
                        width: 40,
                        height: 40,
                        borderRadius: 2,
                        bgcolor: "#f1f5f9",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <CakeIcon sx={{ fontSize: 20, color: "#64748b" }} />
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Date of Birth
                      </Typography>
                      <Typography variant="body2" fontWeight={500}>
                        {new Date(patient.date_of_birth).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                        })}
                      </Typography>
                    </Box>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Medical History Card */}
        <Grid item xs={12} md={8}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: "0 4px 20px rgba(0, 0, 0, 0.05)",
              border: "1px solid #e2e8f0",
              height: "100%",
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
                <Box display="flex" alignItems="center" gap={1}>
                  <HistoryIcon sx={{ color: "#3b82f6" }} />
                  <Typography variant="h6" fontWeight={600} color="#0f172a">
                    Medical History
                  </Typography>
                  <Chip
                    label={`${patient.history.length} records`}
                    size="small"
                    sx={{
                      ml: 1,
                      bgcolor: "#dbeafe",
                      color: "#1d4ed8",
                      fontWeight: 500,
                    }}
                  />
                </Box>
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={handleAddHistoryOpen}
                  sx={{
                    bgcolor: "#3b82f6",
                    "&:hover": { bgcolor: "#2563eb" },
                    borderRadius: 2,
                    textTransform: "none",
                    fontWeight: 600,
                  }}
                >
                  Add History
                </Button>
              </Box>

              {patient.history.length === 0 && (
                <Box
                  py={6}
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                  justifyContent="center"
                >
                  <HistoryIcon sx={{ fontSize: 48, color: "#cbd5e1", mb: 2 }} />
                  <Typography color="text.secondary">No medical history available</Typography>
                </Box>
              )}

              <Stack spacing={2}>
                {patient.history.map((h) => (
                  <Box
                    key={h.id}
                    p={3}
                    borderRadius={2}
                    sx={{
                      bgcolor: "#f8fafc",
                      border: "1px solid #e2e8f0",
                      transition: "all 0.2s ease",
                      "&:hover": {
                        bgcolor: "#f1f5f9",
                        borderColor: "#cbd5e1",
                      },
                    }}
                  >
                    {/* Date */}
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      {new Date(h.created_at).toLocaleDateString("en-US", {
                        weekday: "long",
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </Typography>

                    <Stack spacing={2} mt={2}>
                      {/* Symptoms */}
                      {h.symptoms && (
                        <Box>
                          <Box display="flex" alignItems="center" gap={1} mb={1}>
                            <LocalHospitalIcon sx={{ fontSize: 16, color: "#3b82f6" }} />
                            <Typography variant="subtitle2" fontWeight={600} color="#0f172a">
                              Symptoms
                            </Typography>
                          </Box>
                          <Typography variant="body2" color="text.secondary" pl={3}>
                            {h.symptoms}
                          </Typography>
                        </Box>
                      )}

                      {/* Medical Conditions */}
                      {h.medical_conditions && h.medical_conditions.length > 0 && (
                        <Box>
                          <Box display="flex" alignItems="center" gap={1} mb={1}>
                            <LocalHospitalIcon sx={{ fontSize: 16, color: "#8b5cf6" }} />
                            <Typography variant="subtitle2" fontWeight={600} color="#0f172a">
                              Medical Conditions
                            </Typography>
                          </Box>
                          <Box display="flex" gap={1} flexWrap="wrap" pl={3}>
                            {h.medical_conditions.map((c) => (
                              <Chip
                                key={c}
                                size="small"
                                label={c}
                                sx={{
                                  bgcolor: "#ede9fe",
                                  color: "#6d28d9",
                                  fontWeight: 500,
                                }}
                              />
                            ))}
                          </Box>
                        </Box>
                      )}

                      {/* Allergies */}
                      {h.allergies && h.allergies.length > 0 && (
                        <Box>
                          <Box display="flex" alignItems="center" gap={1} mb={1}>
                            <WarningIcon sx={{ fontSize: 16, color: "#f59e0b" }} />
                            <Typography variant="subtitle2" fontWeight={600} color="#0f172a">
                              Allergies
                            </Typography>
                          </Box>
                          <Box display="flex" gap={1} flexWrap="wrap" pl={3}>
                            {h.allergies.map((a) => (
                              <Chip
                                key={a}
                                size="small"
                                label={a}
                                sx={{
                                  bgcolor: "#fef3c7",
                                  color: "#b45309",
                                  fontWeight: 500,
                                }}
                              />
                            ))}
                          </Box>
                        </Box>
                      )}

                      {/* Notes */}
                      {h.notes && (
                        <Box>
                          <Box display="flex" alignItems="center" gap={1} mb={1}>
                            <NotesIcon sx={{ fontSize: 16, color: "#64748b" }} />
                            <Typography variant="subtitle2" fontWeight={600} color="#0f172a">
                              Notes
                            </Typography>
                          </Box>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            pl={3}
                            sx={{
                              bgcolor: "#ffffff",
                              p: 2,
                              borderRadius: 1,
                              border: "1px solid #e2e8f0",
                            }}
                          >
                            {h.notes}
                          </Typography>
                        </Box>
                      )}
                    </Stack>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Add Medical History Dialog */}
      <Dialog
        open={addHistoryOpen}
        onClose={handleAddHistoryClose}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle sx={{ fontWeight: 700, color: "#0f172a" }}>
          Add Medical History
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField
              label="Symptoms"
              multiline
              rows={2}
              fullWidth
              value={addHistoryForm.symptoms}
              onChange={(e) =>
                setAddHistoryForm({ ...addHistoryForm, symptoms: e.target.value })
              }
              placeholder="Describe the patient's symptoms..."
            />
            <TextField
              label="Medical Conditions"
              fullWidth
              value={addHistoryForm.medical_conditions}
              onChange={(e) =>
                setAddHistoryForm({ ...addHistoryForm, medical_conditions: e.target.value })
              }
              placeholder="Enter conditions separated by commas (e.g., Diabetes, Hypertension)"
              helperText="Separate multiple conditions with commas"
            />
            <TextField
              label="Allergies"
              fullWidth
              value={addHistoryForm.allergies}
              onChange={(e) =>
                setAddHistoryForm({ ...addHistoryForm, allergies: e.target.value })
              }
              placeholder="Enter allergies separated by commas (e.g., Penicillin, Peanuts)"
              helperText="Separate multiple allergies with commas"
            />
            <TextField
              label="Notes"
              multiline
              rows={3}
              fullWidth
              value={addHistoryForm.notes}
              onChange={(e) =>
                setAddHistoryForm({ ...addHistoryForm, notes: e.target.value })
              }
              placeholder="Additional notes about the patient..."
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleAddHistoryClose} sx={{ textTransform: "none" }}>
            Cancel
          </Button>
          <Button
            onClick={handleAddHistorySubmit}
            variant="contained"
            disabled={addHistoryLoading}
            sx={{
              bgcolor: "#3b82f6",
              "&:hover": { bgcolor: "#2563eb" },
              textTransform: "none",
              fontWeight: 600,
            }}
          >
            {addHistoryLoading ? <CircularProgress size={24} /> : "Add History"}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
};

export default PatientDetailPage;
