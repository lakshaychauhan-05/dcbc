import { useEffect, useState } from 'react';
import { adminApi, normalizeDoctorsResponse } from '../../services/api';
import type { Doctor, Clinic } from '../../types';

const Doctors = () => {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    phone_number: '',
    specialization: '',
    experience_years: 0,
    languages: '',
    consultation_type: 'in_person',
    clinic_id: '',
    initial_password: '',
  });

  const showMessage = (msg: string, isError = false) => {
    if (isError) { setError(msg); setSuccess(''); }
    else { setSuccess(msg); setError(''); }
    setTimeout(() => { setError(''); setSuccess(''); }, 4000);
  };

  const fetchData = async () => {
    try {
      const [doctorsRes, clinicsRes] = await Promise.all([
        adminApi.get('/doctors'),
        adminApi.get('/clinics'),
      ]);
      setDoctors(normalizeDoctorsResponse(doctorsRes.data) as Doctor[]);
      setClinics(clinicsRes.data.clinics || clinicsRes.data || []);
    } catch (err) {
      console.error('Failed to fetch data:', err);
      showMessage('Failed to load data. Please refresh.', true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setError('');
    try {
      const payload: Record<string, unknown> = {
        email: formData.email,
        name: formData.name,
        phone_number: formData.phone_number || undefined,
        specialization: formData.specialization,
        experience_years: formData.experience_years,
        languages: formData.languages.split(',').map((l) => l.trim()).filter(Boolean),
        consultation_type: formData.consultation_type,
        clinic_id: formData.clinic_id || undefined,
      };

      if (editingDoctor) {
        await adminApi.put(`/doctors/${editingDoctor.email}`, payload);
        showMessage('Doctor updated successfully.');
      } else {
        if (formData.initial_password) {
          payload.initial_password = formData.initial_password;
        }
        await adminApi.post('/doctors', payload);
        showMessage('Doctor created successfully.');
      }
      setShowModal(false);
      setEditingDoctor(null);
      resetForm();
      fetchData();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      showMessage(e.response?.data?.detail || 'Failed to save doctor.', true);
    } finally {
      setActionLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      email: '',
      name: '',
      phone_number: '',
      specialization: '',
      experience_years: 0,
      languages: '',
      consultation_type: 'in_person',
      clinic_id: '',
      initial_password: '',
    });
  };

  const handleEdit = (doctor: Doctor) => {
    setEditingDoctor(doctor);
    setFormData({
      email: doctor.email,
      name: doctor.name,
      phone_number: doctor.phone_number || '',
      specialization: doctor.specialization,
      experience_years: doctor.experience_years,
      languages: doctor.languages?.join(', ') || '',
      consultation_type: doctor.consultation_type,
      clinic_id: doctor.clinic_id || '',
      initial_password: '',
    });
    setShowModal(true);
  };

  const handleDelete = async (email: string) => {
    if (!confirm(`Deactivate doctor ${email}? They will be marked inactive.`)) return;
    try {
      await adminApi.delete(`/doctors/${email}`);
      showMessage('Doctor deactivated.');
      fetchData();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      showMessage(e.response?.data?.detail || 'Failed to deactivate doctor.', true);
    }
  };

  const handleCreatePortalAccount = async (email: string) => {
    const password = prompt('Enter initial password for the portal account (leave blank to auto-generate):');
    if (password === null) return; // user cancelled
    try {
      const body = password ? { password } : {};
      const res = await adminApi.post(`/doctors/${email}/portal-account`, body);
      const generated: string = res.data?.password;
      if (generated && generated !== password) {
        alert(`Portal account created.\nGenerated password: ${generated}\nPlease save this — it cannot be recovered.`);
      } else {
        showMessage('Portal account created successfully.');
      }
      fetchData();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      showMessage(e.response?.data?.detail || 'Failed to create portal account.', true);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <span className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 mb-1">Doctors</h1>
          <p className="text-slate-500">Manage doctor profiles</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => { setEditingDoctor(null); resetForm(); setShowModal(true); }}
        >
          Add Doctor
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
          {success}
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Specialization</th>
                <th>Experience</th>
                <th>Clinic</th>
                <th>Status</th>
                <th>Portal</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {doctors.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-500">
                    No doctors found
                  </td>
                </tr>
              ) : (
                doctors.map((doctor) => (
                  <tr key={doctor.email}>
                    <td className="font-medium">{doctor.name}</td>
                    <td>{doctor.email}</td>
                    <td>{doctor.specialization}</td>
                    <td>{doctor.experience_years} yrs</td>
                    <td>{doctor.clinic_name || '-'}</td>
                    <td>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        doctor.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {doctor.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      {doctor.has_portal_account ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">
                          Active
                        </span>
                      ) : (
                        <button
                          className="text-blue-600 text-sm hover:underline"
                          onClick={() => handleCreatePortalAccount(doctor.email)}
                        >
                          Create Account
                        </button>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary mr-2"
                        onClick={() => handleEdit(doctor)}
                      >
                        Edit
                      </button>
                      {doctor.is_active && (
                        <button
                          className="btn btn-danger"
                          onClick={() => handleDelete(doctor.email)}
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                {editingDoctor ? 'Edit Doctor' : 'Add Doctor'}
              </h2>
              <button onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Email *</label>
                  <input
                    type="email"
                    className="form-input"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    disabled={!!editingDoctor}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Name *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.phone_number}
                    onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Specialization *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.specialization}
                    onChange={(e) => setFormData({ ...formData, specialization: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Experience (years)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={formData.experience_years}
                    onChange={(e) => setFormData({ ...formData, experience_years: parseInt(e.target.value) || 0 })}
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Languages (comma-separated)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.languages}
                    onChange={(e) => setFormData({ ...formData, languages: e.target.value })}
                    placeholder="English, Hindi"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Consultation Type</label>
                  <select
                    className="form-input"
                    value={formData.consultation_type}
                    onChange={(e) => setFormData({ ...formData, consultation_type: e.target.value })}
                  >
                    <option value="in_person">In-Person</option>
                    <option value="online">Online</option>
                    <option value="both">Both</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Clinic</label>
                  <select
                    className="form-input"
                    value={formData.clinic_id}
                    onChange={(e) => setFormData({ ...formData, clinic_id: e.target.value })}
                  >
                    <option value="">Select a clinic</option>
                    {clinics.map((clinic) => (
                      <option key={clinic.id} value={clinic.id}>
                        {clinic.name}
                      </option>
                    ))}
                  </select>
                </div>
                {!editingDoctor && (
                  <div className="form-group">
                    <label className="form-label">Initial Portal Password (optional)</label>
                    <input
                      type="password"
                      className="form-input"
                      value={formData.initial_password}
                      onChange={(e) => setFormData({ ...formData, initial_password: e.target.value })}
                      placeholder="Leave blank to skip portal account creation"
                    />
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowModal(false)}
                  disabled={actionLoading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={actionLoading}>
                  {actionLoading ? 'Saving...' : editingDoctor ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Doctors;
