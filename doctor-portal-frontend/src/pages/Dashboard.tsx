import { useEffect, useState } from "react";
import { Box, Card, CardContent, Grid, Stack, Typography, Chip } from "@mui/material";
import api from "../services/api";
import { AppointmentItem, DoctorProfile } from "../types";

type OverviewResponse = {
  doctor: DoctorProfile;
  upcoming_appointments: AppointmentItem[];
};

const Dashboard = () => {
  const [overview, setOverview] = useState<OverviewResponse | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const res = await api.get<OverviewResponse>("/dashboard/overview");
      setOverview(res.data);
    };
    fetchData();
  }, []);

  const upcoming = overview?.upcoming_appointments ?? [];

  return (
    <Stack spacing={3}>
      <Typography variant="h5" fontWeight={700}>
        Overview
      </Typography>

      {overview && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  Doctor
                </Typography>
                <Typography variant="h6" fontWeight={700}>
                  {overview.doctor.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {overview.doctor.specialization} · {overview.doctor.experience_years} yrs
                </Typography>
                <Box mt={1} display="flex" gap={1} flexWrap="wrap">
                  {overview.doctor.languages.map((lang) => (
                    <Chip key={lang} size="small" label={lang} />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  Upcoming appointments
                </Typography>
                <Stack spacing={2} mt={2}>
                  {upcoming.length === 0 && <Typography>No upcoming appointments.</Typography>}
                  {upcoming.map((appt) => (
                    <Box
                      key={appt.id}
                      p={2}
                      border="1px solid #e2e8f0"
                      borderRadius={2}
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                    >
                      <Box>
                        <Typography fontWeight={700}>{appt.patient.name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {appt.date} · {appt.start_time} - {appt.end_time} ({appt.timezone})
                        </Typography>
                      </Box>
                      <Chip label={appt.status} color={appt.status === "CANCELLED" ? "error" : "success"} />
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Stack>
  );
};

export default Dashboard;
