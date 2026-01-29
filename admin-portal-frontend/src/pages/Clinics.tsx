import { FormEvent, useEffect, useState } from "react";
import api from "../services/api";

type Clinic = {
  id: string;
  name: string;
  timezone: string;
  address?: string | null;
  is_active: boolean;
  created_at: string;
};

const Clinics = () => {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [address, setAddress] = useState("");
  const [isActive, setIsActive] = useState(true);

  const [forceDelete, setForceDelete] = useState(false);

  const fetchClinics = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get("/clinics");
      setClinics(resp.data.clinics || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load clinics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClinics();
  }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/clinics", {
        name,
        timezone,
        address: address || null,
        is_active: isActive,
      });
      setName("");
      setTimezone("UTC");
      setAddress("");
      setIsActive(true);
      fetchClinics();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create clinic");
    }
  };

  const toggleActive = async (clinic: Clinic) => {
    setError(null);
    try {
      await api.put(`/clinics/${clinic.id}`, { is_active: !clinic.is_active });
      fetchClinics();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to update clinic");
    }
  };

  const deleteClinic = async (id: string) => {
    setError(null);
    try {
      await api.delete(`/clinics/${id}`, { params: { force: forceDelete } });
      fetchClinics();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to delete clinic");
    }
  };

  return (
    <div>
      <h2>Clinics</h2>
      {error && <div style={{ color: "red", marginBottom: 8 }}>{error}</div>}

      <div className="card">
        <h3>Create Clinic</h3>
        <form className="form-grid" onSubmit={handleCreate}>
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <input placeholder="Timezone (e.g., UTC)" value={timezone} onChange={(e) => setTimezone(e.target.value)} required />
          <input placeholder="Address (optional)" value={address} onChange={(e) => setAddress(e.target.value)} />
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Active
          </label>
          <button type="submit" disabled={loading}>{loading ? "Saving..." : "Create"}</button>
        </form>
      </div>

      <div className="card">
        <h3>Existing Clinics</h3>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <input type="checkbox" checked={forceDelete} onChange={(e) => setForceDelete(e.target.checked)} />
          Force delete clinics with doctors
        </label>
        {loading ? (
          <div>Loading...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Timezone</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clinics.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.timezone}</td>
                  <td>
                    <span className="badge">{c.is_active ? "Active" : "Inactive"}</span>
                  </td>
                  <td style={{ display: "flex", gap: 8 }}>
                    <button className="secondary" onClick={() => toggleActive(c)}>
                      {c.is_active ? "Deactivate" : "Activate"}
                    </button>
                    <button className="secondary" onClick={() => deleteClinic(c.id)}>
                      Delete
                    </button>
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

export default Clinics;
