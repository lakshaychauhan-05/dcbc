import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import api, { normalizeDoctorsResponse } from "../services/api";
import { useToast } from "../contexts/ToastContext";
import ConfirmDialog from "../components/ConfirmDialog";
import Modal from "../components/Modal";

type Clinic = {
  id: string;
  name: string;
};

type Doctor = {
  email: string;
  name: string;
  phone_number?: string;
  clinic_id: string;
  specialization: string;
  is_active: boolean;
  experience_years: number;
  languages: string[] | string;
  consultation_type: string;
  working_days: string[];
  working_hours: { start: string; end: string };
  timezone: string;
};

const Doctors = () => {
  const { addToast } = useToast();
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filterClinicId, setFilterClinicId] = useState<string>("");
  const [filterClinicIdInput, setFilterClinicIdInput] = useState("");

  const [deleteTarget, setDeleteTarget] = useState<{ email: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [assignTarget, setAssignTarget] = useState<Doctor | null>(null);
  const [assignClinicId, setAssignClinicId] = useState("");
  const [assigning, setAssigning] = useState(false);

  const [clinicId, setClinicId] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
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
  const [initialPassword, setInitialPassword] = useState("");
  const [creating, setCreating] = useState(false);

  const [provisioning, setProvisioning] = useState<string | null>(null);

  const clinicOptions = useMemo(() => clinics.map((c) => ({ value: c.id, label: c.name })), [clinics]);
  const clinicMap = useMemo(() => {
    const m: Record<string, string> = {};
    clinics.forEach((c) => (m[c.id] = c.name));
    return m;
  }, [clinics]);

  const fetchClinics = useCallback(async () => {
    try {
      const resp = await api.get("/clinics");
      const list = resp.data.clinics || [];
      setClinics(list);
      if (!clinicId && list.length) setClinicId(list[0].id);
    } catch {
      // ignore
    }
  }, [clinicId]);

  const fetchDoctors = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { limit: number; clinic_id?: string } = { limit: 200 };
      if (filterClinicId) params.clinic_id = filterClinicId;
      const resp = await api.get("/doctors", { params });
      const list = normalizeDoctorsResponse(resp.data);
      setDoctors(list);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to load doctors";
      setError(Array.isArray(msg) ? msg[0]?.msg ?? msg : msg);
    } finally {
      setLoading(false);
    }
  }, [filterClinicId]);

  useEffect(() => {
    fetchClinics();
  }, [fetchClinics]);

  useEffect(() => {
    fetchDoctors();
  }, [fetchDoctors]);

  const applyFilterByClinicId = () => {
    const id = filterClinicIdInput.trim();
    if (id) setFilterClinicId(id);
    else setFilterClinicId("");
  };

  const clearFilter = () => {
    setFilterClinicId("");
    setFilterClinicIdInput("");
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const payload: Record<string, any> = {
        clinic_id: clinicId,
        name,
        email,
        phone_number: phoneNumber.trim() || null,
        specialization,
        experience_years: Number(experienceYears),
        languages: typeof languages === "string" ? languages.split(",").map((l) => l.trim()).filter(Boolean) : languages,
        consultation_type: consultationType,
        general_working_days_text: generalWorkingDaysText || null,
        working_days: workingDays.split(",").map((d) => d.trim().toLowerCase()),
        working_hours: { start: workingStart, end: workingEnd },
        slot_duration_minutes: Number(slotDuration),
        timezone,
      };
      // Include initial password if provided
      if (initialPassword.trim()) {
        payload.initial_password = initialPassword.trim();
      }
      const response = await api.post("/doctors", payload);
      if (response.data?.portal_account_created) {
        addToast("Doctor created with portal login ready! Please securely share the password with the doctor.", "success");
      } else if (response.data?.portal_account_note) {
        addToast(`Doctor created. ${response.data.portal_account_note}`, "success");
      } else {
        addToast("Doctor created successfully", "success");
      }
      setName("");
      setEmail("");
      setPhoneNumber("");
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
      setInitialPassword("");
      fetchDoctors();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to create doctor";
      setError(Array.isArray(msg) ? msg[0]?.msg ?? msg : msg);
      addToast(Array.isArray(msg) ? msg[0]?.msg ?? String(msg) : String(msg), "error");
    } finally {
      setCreating(false);
    }
  };

  const openDeleteConfirm = (d: Doctor) => setDeleteTarget({ email: d.email, name: d.name });

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setError(null);
    try {
      await api.delete(`/doctors/${encodeURIComponent(deleteTarget.email)}`);
      addToast("Doctor removed", "success");
      setDeleteTarget(null);
      fetchDoctors();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to remove doctor";
      addToast(Array.isArray(msg) ? msg[0]?.msg ?? String(msg) : String(msg), "error");
    } finally {
      setDeleting(false);
    }
  };

  const toggleDoctorActive = async (doctor: Doctor) => {
    setError(null);
    try {
      await api.put(`/doctors/${encodeURIComponent(doctor.email)}`, { is_active: !doctor.is_active });
      addToast(doctor.is_active ? "Doctor deactivated" : "Doctor activated", "success");
      fetchDoctors();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to update doctor";
      addToast(Array.isArray(msg) ? msg[0]?.msg ?? String(msg) : String(msg), "error");
    }
  };

  const openAssignModal = (d: Doctor) => {
    setAssignTarget(d);
    setAssignClinicId("");
  };

  const submitAssign = async (e: FormEvent) => {
    e.preventDefault();
    if (!assignTarget || !assignClinicId.trim()) return;
    setAssigning(true);
    setError(null);
    try {
      await api.put(`/doctors/${encodeURIComponent(assignTarget.email)}`, {
        clinic_id: assignClinicId.trim(),
      });
      addToast(`Doctor assigned to ${clinicMap[assignClinicId.trim()] ?? "clinic"}`, "success");
      setAssignTarget(null);
      setAssignClinicId("");
      fetchDoctors();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to assign doctor";
      addToast(Array.isArray(msg) ? msg[0]?.msg ?? String(msg) : String(msg), "error");
    } finally {
      setAssigning(false);
    }
  };

  const provisionPortalAccount = async (email: string) => {
    setError(null);
    setProvisioning(email);
    try {
      const resp = await api.post(`/doctors/${encodeURIComponent(email)}/portal-account`);
      const password = resp.data?.password;
      if (password) {
        // Log password to console for secure retrieval, don't show in UI
        console.info(`[ADMIN] Portal account password for ${email} - check response in Network tab or copy from here:`, password);
        addToast("Portal account provisioned. Check browser console (F12) for the temporary password.", "success");
      } else {
        addToast("Portal account provisioned", "success");
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to provision portal account";
      addToast(Array.isArray(msg) ? msg[0]?.msg ?? String(msg) : String(msg), "error");
    } finally {
      setProvisioning(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Doctors</h1>
        <p>Create doctors, assign them to clinics by clinic ID, and manage portal accounts.</p>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      <div className="card">
        <h2 className="card-title">Create doctor</h2>
        {clinicOptions.length === 0 ? (
          <div className="empty-state">
            <p>No clinics yet</p>
            <span>Create a clinic first from the Clinics page.</span>
          </div>
        ) : (
          <form className="form-grid" onSubmit={handleCreate}>
            <div className="form-group">
              <label htmlFor="create-clinic">Clinic</label>
              <select
                id="create-clinic"
                value={clinicId}
                onChange={(e) => setClinicId(e.target.value)}
                required
              >
                {clinicOptions.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="doctor-name">Name</label>
              <input id="doctor-name" placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-email">Email</label>
              <input id="doctor-email" type="email" placeholder="doctor@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-phone">Phone Number</label>
              <input
                id="doctor-phone"
                type="tel"
                placeholder="9876543210 or +919876543210"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
              />
              <small style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                10 digits starting with 6-9, optional +91 prefix. Used for SMS notifications.
              </small>
            </div>
            <div className="form-group">
              <label htmlFor="doctor-password">Initial Password (for Portal Login)</label>
              <input
                id="doctor-password"
                type="text"
                placeholder="e.g. Password123"
                value={initialPassword}
                onChange={(e) => setInitialPassword(e.target.value)}
              />
              <small style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                Set a password so the doctor can log into the Doctor Portal. Leave empty to set later.
              </small>
            </div>
            <div className="form-group">
              <label htmlFor="doctor-spec">Specialization</label>
              <input id="doctor-spec" placeholder="e.g. General" value={specialization} onChange={(e) => setSpecialization(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-exp">Experience (years)</label>
              <input id="doctor-exp" type="number" min={0} value={experienceYears} onChange={(e) => setExperienceYears(Number(e.target.value))} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-lang">Languages (comma separated)</label>
              <input id="doctor-lang" placeholder="english, spanish" value={languages} onChange={(e) => setLanguages(e.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-consult">Consultation type</label>
              <input id="doctor-consult" placeholder="in-person" value={consultationType} onChange={(e) => setConsultationType(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-days">Working days (comma)</label>
              <input id="doctor-days" placeholder="monday,tuesday,..." value={workingDays} onChange={(e) => setWorkingDays(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-start">Start time</label>
              <input id="doctor-start" placeholder="09:00" value={workingStart} onChange={(e) => setWorkingStart(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-end">End time</label>
              <input id="doctor-end" placeholder="17:00" value={workingEnd} onChange={(e) => setWorkingEnd(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-slot">Slot duration (min)</label>
              <input id="doctor-slot" type="number" min={5} max={240} value={slotDuration} onChange={(e) => setSlotDuration(Number(e.target.value))} required />
            </div>
            <div className="form-group">
              <label htmlFor="doctor-tz">Timezone</label>
              <input id="doctor-tz" placeholder="UTC" value={timezone} onChange={(e) => setTimezone(e.target.value)} required />
            </div>
            <div className="form-group" style={{ alignSelf: "end" }}>
              <button type="submit" disabled={creating}>
                {creating ? "Creating…" : "Create doctor"}
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="card">
        <h2 className="card-title">Existing doctors</h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end", marginBottom: 16 }}>
          <div className="form-group" style={{ margin: 0, minWidth: 200 }}>
            <label htmlFor="filter-clinic">Filter by clinic</label>
            <select
              id="filter-clinic"
              value={filterClinicId}
              onChange={(e) => {
                setFilterClinicId(e.target.value);
                setFilterClinicIdInput("");
              }}
            >
              <option value="">All clinics</option>
              {clinicOptions.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0, minWidth: 220 }}>
            <label htmlFor="filter-clinic-id">Or by clinic ID</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                id="filter-clinic-id"
                placeholder="Paste clinic UUID"
                value={filterClinicIdInput}
                onChange={(e) => setFilterClinicIdInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), applyFilterByClinicId())}
              />
              <button type="button" className="btn-secondary" onClick={applyFilterByClinicId}>
                Apply
              </button>
            </div>
          </div>
          {(filterClinicId || filterClinicIdInput) && (
            <button type="button" className="btn-ghost btn-sm" onClick={clearFilter}>
              Clear filter
            </button>
          )}
        </div>

        {loading ? (
          <div className="loading-row">
            <span className="spinner" aria-hidden /> Loading doctors…
          </div>
        ) : doctors.length === 0 ? (
          <div className="empty-state">
            <p>No doctors found</p>
            <span>
              {filterClinicId || filterClinicIdInput
                ? "Try changing the filter or create a doctor for this clinic."
                : "Create your first doctor using the form above."}
            </span>
            <span style={{ display: "block", marginTop: 12, fontSize: "0.875rem", color: "var(--text-muted)" }}>
              If you expect data: ensure Core API (port 8000) and Admin API (port 5050) are running, and SERVICE_API_KEY matches in .env.
            </span>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Clinic</th>
                  <th>Specialization</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {doctors.map((d) => (
                  <tr key={d.email}>
                    <td>{d.name}</td>
                    <td>{d.email}</td>
                    <td>
                      <span title={d.clinic_id}>{clinicMap[d.clinic_id] ?? d.clinic_id}</span>
                    </td>
                    <td>{d.specialization}</td>
                    <td>
                      <span className={`badge ${d.is_active ? "badge-active" : "badge-inactive"}`}>
                        {d.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td>
                      <div className="cell-actions">
                        <button type="button" className="btn-primary btn-sm" onClick={() => openAssignModal(d)}>
                          Assign to clinic
                        </button>
                        <button type="button" className="btn-secondary btn-sm" onClick={() => toggleDoctorActive(d)}>
                          {d.is_active ? "Deactivate" : "Activate"}
                        </button>
                        <button type="button" className="btn-secondary btn-sm" onClick={() => provisionPortalAccount(d.email)} disabled={!!provisioning}>
                          {provisioning === d.email ? "…" : "Portal"}
                        </button>
                        <button type="button" className="btn-danger btn-sm" onClick={() => openDeleteConfirm(d)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="Remove doctor"
        message={deleteTarget ? `Remove "${deleteTarget.name}" (${deleteTarget.email})? This cannot be undone.` : ""}
        confirmLabel="Remove"
        cancelLabel="Cancel"
        variant="danger"
        loading={deleting}
      />

      <Modal
        isOpen={!!assignTarget}
        onClose={() => { setAssignTarget(null); setAssignClinicId(""); }}
        title={assignTarget ? `Assign "${assignTarget.name}" to clinic` : "Assign to clinic"}
        size="md"
      >
        {assignTarget && (
          <form onSubmit={submitAssign}>
            <p style={{ margin: "0 0 16px 0", color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
              Enter the clinic ID (UUID) to assign this doctor to, or choose from the list.
            </p>
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label htmlFor="assign-clinic">Clinic</label>
              <select
                id="assign-clinic"
                value={assignClinicId}
                onChange={(e) => setAssignClinicId(e.target.value)}
              >
                <option value="">Select or paste ID below</option>
                {clinicOptions.filter((c) => c.value !== assignTarget.clinic_id).map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: 20 }}>
              <label htmlFor="assign-clinic-id">Or paste clinic ID</label>
              <input
                id="assign-clinic-id"
                placeholder="Clinic UUID"
                value={assignClinicId}
                onChange={(e) => setAssignClinicId(e.target.value)}
              />
            </div>
            <div className="confirm-actions">
              <button type="button" className="btn-secondary" onClick={() => { setAssignTarget(null); setAssignClinicId(""); }}>
                Cancel
              </button>
              <button type="submit" disabled={assigning || !assignClinicId.trim()}>
                {assigning ? "Assigning…" : "Assign to clinic"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};

export default Doctors;
