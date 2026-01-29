import { FormEvent, useEffect, useMemo, useState } from "react";
import api from "../services/api";

type Clinic = {
  id: string;
  name: string;
};

type Doctor = {
  email: string;
  name: string;
  clinic_id: string;
  specialization: string;
  is_active: boolean;
  experience_years: number;
  languages: string[];
  consultation_type: string;
  working_days: string[];
  working_hours: { start: string; end: string };
  timezone: string;
};

const Doctors = () => {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [clinicId, setClinicId] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [experienceYears, setExperienceYears] = useState(1);
  const [languages, setLanguages] = useState("english");
  const [consultationType, setConsultationType] = useState("in-person");
  const [generalWorkingDaysText, setGeneralWorkingDaysText] = useState("");
  const [workingDays, setWorkingDays] = useState("monday,tuesday,wednesday,thursday,friday");
  const [workingStart, setWorkingStart] = useState("09:00");
  const [workingEnd, setWorkingEnd] = useState("17:00");
  const [slotDuration, setSlotDuration] = useState(30);
  const [timezone, setTimezone] = useState("UTC");

  const clinicOptions = useMemo(() => clinics.map((c) => ({ value: c.id, label: c.name })), [clinics]);

  const fetchClinics = async () => {
    try {
      const resp = await api.get("/clinics");
      setClinics(resp.data.clinics || []);
      if (!clinicId && resp.data.clinics?.length) {
        setClinicId(resp.data.clinics[0].id);
      }
    } catch (err: any) {
      // ignore, surfaced elsewhere
    }
  };

  const fetchDoctors = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get("/doctors", { params: { limit: 200 } });
      setDoctors(resp.data.doctors || resp.data?.doctors || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load doctors");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClinics();
    fetchDoctors();
  }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const payload = {
        clinic_id: clinicId,
        name,
        email,
        specialization,
        experience_years: Number(experienceYears),
        languages: languages.split(",").map((l) => l.trim()).filter(Boolean),
        consultation_type: consultationType,
        general_working_days_text: generalWorkingDaysText || null,
        working_days: workingDays.split(",").map((d) => d.trim().toLowerCase()),
        working_hours: { start: workingStart, end: workingEnd },
        slot_duration_minutes: Number(slotDuration),
        timezone,
      };
      await api.post("/doctors", payload);
      setName("");
      setEmail("");
      setSpecialization("");
      setExperienceYears(1);
      setLanguages("english");
      setConsultationType("in-person");
      setGeneralWorkingDaysText("");
      setWorkingDays("monday,tuesday,wednesday,thursday,friday");
      setWorkingStart("09:00");
      setWorkingEnd("17:00");
      setSlotDuration(30);
      setTimezone("UTC");
      fetchDoctors();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create doctor");
    }
  };

  const deleteDoctor = async (email: string) => {
    setError(null);
    try {
      await api.delete(`/doctors/${email}`);
      fetchDoctors();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to delete doctor");
    }
  };

  const toggleDoctorActive = async (doctor: Doctor) => {
    setError(null);
    try {
      await api.put(`/doctors/${doctor.email}`, { is_active: !doctor.is_active });
      fetchDoctors();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to update doctor");
    }
  };

  const provisionPortalAccount = async (email: string) => {
    setError(null);
    try {
      const resp = await api.post(`/doctors/${email}/portal-account`);
      const password = resp.data?.password;
      alert(password ? `Portal account provisioned.\nTemporary password: ${password}` : "Portal account provisioned");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to provision portal account");
    }
  };

  return (
    <div>
      <h2>Doctors</h2>
      {error && <div style={{ color: "red", marginBottom: 8 }}>{error}</div>}

      <div className="card">
        <h3>Create Doctor</h3>
        {clinicOptions.length === 0 ? (
          <div>Please create a clinic first.</div>
        ) : (
          <form className="form-grid" onSubmit={handleCreate}>
            <select value={clinicId} onChange={(e) => setClinicId(e.target.value)} required>
              {clinicOptions.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
            <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <input placeholder="Specialization" value={specialization} onChange={(e) => setSpecialization(e.target.value)} required />
            <input type="number" min={0} placeholder="Experience years" value={experienceYears} onChange={(e) => setExperienceYears(Number(e.target.value))} required />
            <input placeholder="Languages (comma separated)" value={languages} onChange={(e) => setLanguages(e.target.value)} />
            <input placeholder="Consultation type" value={consultationType} onChange={(e) => setConsultationType(e.target.value)} required />
            <textarea placeholder="General working days text (optional)" value={generalWorkingDaysText} onChange={(e) => setGeneralWorkingDaysText(e.target.value)} />
            <input placeholder="Working days (comma, e.g., monday,tuesday)" value={workingDays} onChange={(e) => setWorkingDays(e.target.value)} required />
            <input placeholder="Start time (HH:MM)" value={workingStart} onChange={(e) => setWorkingStart(e.target.value)} required />
            <input placeholder="End time (HH:MM)" value={workingEnd} onChange={(e) => setWorkingEnd(e.target.value)} required />
            <input type="number" min={5} max={240} placeholder="Slot duration minutes" value={slotDuration} onChange={(e) => setSlotDuration(Number(e.target.value))} required />
            <input placeholder="Timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)} required />
            <button type="submit" disabled={loading}>{loading ? "Saving..." : "Create doctor"}</button>
          </form>
        )}
      </div>

      <div className="card">
        <h3>Existing Doctors</h3>
        {loading ? (
          <div>Loading...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Clinic</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {doctors.map((d) => (
                <tr key={d.email}>
                  <td>{d.name}</td>
                  <td>{d.email}</td>
                  <td>{d.clinic_id}</td>
                  <td>
                    <span className="badge">{d.is_active ? "Active" : "Inactive"}</span>
                  </td>
                  <td style={{ display: "flex", gap: 8 }}>
                    <button className="secondary" onClick={() => toggleDoctorActive(d)}>
                      {d.is_active ? "Deactivate" : "Activate"}
                    </button>
                    <button className="secondary" onClick={() => deleteDoctor(d.email)}>Delete</button>
                    <button onClick={() => provisionPortalAccount(d.email)}>Portal Account</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default Doctors;
