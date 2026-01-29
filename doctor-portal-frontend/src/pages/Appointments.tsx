import { useEffect, useState } from "react";
import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import api from "../services/api";
import { AppointmentItem } from "../types";

type AppointmentsResponse = {
  appointments: AppointmentItem[];
};

const Appointments = () => {
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      const res = await api.get<AppointmentsResponse>("/dashboard/appointments");
      setAppointments(res.data.appointments);
    };
    fetchData();
  }, []);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" fontWeight={700}>
        Appointments
      </Typography>
      <Stack spacing={2}>
        {appointments.map((appt) => (
          <Card key={appt.id}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography fontWeight={700}>{appt.patient.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {appt.date} · {appt.start_time} - {appt.end_time} ({appt.timezone})
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {appt.patient.mobile_number || ""} {appt.patient.email ? `· ${appt.patient.email}` : ""}
                  </Typography>
                </Box>
                <Chip label={appt.status} color={appt.status === "CANCELLED" ? "error" : "primary"} />
              </Box>
            </CardContent>
          </Card>
        ))}
        {appointments.length === 0 && <Typography>No appointments found.</Typography>}
      </Stack>
    </Stack>
  );
};

export default Appointments;
