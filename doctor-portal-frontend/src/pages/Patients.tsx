import { useEffect, useState } from "react";
import { Card, CardContent, Stack, Typography, Button } from "@mui/material";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { PatientSummary } from "../types";

type PatientsResponse = {
  patients: PatientSummary[];
};

const Patients = () => {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      const res = await api.get<PatientsResponse>("/dashboard/patients");
      setPatients(res.data.patients);
    };
    fetchData();
  }, []);

  return (
    <Stack spacing={3}>
      <Typography variant="h5" fontWeight={700}>
        Patients
      </Typography>
      <Stack spacing={2}>
        {patients.map((p) => (
          <Card key={p.id}>
            <CardContent sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <Typography fontWeight={700}>{p.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {p.mobile_number || "No phone"} {p.email ? `· ${p.email}` : ""}
                </Typography>
              </div>
              <Button variant="outlined" size="small" onClick={() => navigate(`/patients/${p.id}`)}>
                View
              </Button>
            </CardContent>
          </Card>
        ))}
        {patients.length === 0 && <Typography>No patients found.</Typography>}
      </Stack>
    </Stack>
  );
};

export default Patients;
