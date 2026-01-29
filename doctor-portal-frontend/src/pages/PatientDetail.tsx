import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import api from "../services/api";
import { PatientDetail as PatientDetailType } from "../types";

const PatientDetail = () => {
  const { id } = useParams();
  const [patient, setPatient] = useState<PatientDetailType | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!id) return;
      try {
        const res = await api.get<PatientDetailType>(`/dashboard/patients/${id}`);
        setPatient(res.data);
      } catch (err) {
        setPatient(null);
      }
    };
    fetchData();
  }, [id]);

  if (!patient) {
    return <Typography>Loading patient...</Typography>;
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h5" fontWeight={700}>
        {patient.name}
      </Typography>
      <Card>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary">
            Contact
          </Typography>
          <Typography>{patient.mobile_number || "No phone"}</Typography>
          <Typography>{patient.email || "No email"}</Typography>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            History
          </Typography>
          <Stack spacing={2}>
            {patient.history.length === 0 && <Typography>No history available.</Typography>}
            {patient.history.map((h) => (
              <Box key={h.id} p={2} border="1px solid #e2e8f0" borderRadius={2}>
                <Typography fontWeight={700}>{new Date(h.created_at).toLocaleString()}</Typography>
                {h.symptoms && <Typography>Symptoms: {h.symptoms}</Typography>}
                {h.medical_conditions && h.medical_conditions.length > 0 && (
                  <Box display="flex" gap={1} mt={1} flexWrap="wrap">
                    {h.medical_conditions.map((c) => (
                      <Chip key={c} size="small" label={c} />
                    ))}
                  </Box>
                )}
                {h.allergies && h.allergies.length > 0 && (
                  <Box display="flex" gap={1} mt={1} flexWrap="wrap">
                    {h.allergies.map((a) => (
                      <Chip key={a} size="small" color="warning" label={a} />
                    ))}
                  </Box>
                )}
                {h.notes && (
                  <Typography variant="body2" color="text.secondary" mt={1}>
                    Notes: {h.notes}
                  </Typography>
                )}
              </Box>
            ))}
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
};

export default PatientDetail;
