import { useEffect, useState } from 'react';
import { adminApi, normalizeDoctorsResponse } from '../../services/api';
import type { Doctor, Clinic } from '../../types';

const Doctors = () => {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    phone_number: '',
    specialization: '',
    experience_years: 0,
    languages: '',
    consultation_type: 'in-person',
    clinic_id: '',
  });

  const fetchData = async () => {
    try {
      const [doctorsRes, clinicsRes] = await Promise.all([
        adminApi.get('/doctors'),
        adminApi.get('/clinics'),
      ]);
      setDoctors(normalizeDoctorsResponse(doctorsRes.data) as Doctor[]);
      setClinics(clinicsRes.data.clinics || clinicsRes.data || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        languages: formData.languages.split(',').map(l => l.trim()).filter(Boolean),
        clinic_id: formData.clinic_id || undefined,
      };

      if (editingDoctor) {
        await adminApi.put(`/doctors/${editingDoctor.email}`, payload);
      } else {
        await adminApi.post('/doctors', payload);
      }
      setShowModal(false);
      setEditingDoctor(null);
      resetForm();
      fetchData();
    } catch (error) {
      console.error('Failed to save doctor:', error);
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
      consultation_type: 'in-person',
      clinic_id: '',
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
    });
    setShowModal(true);
  };

  const handleDelete = async (email: string) => {
    if (!confirm('Are you sure you want to delete this doctor?')) return;
    try {
      await adminApi.delete(`/doctors/${email}`);
      fetchData();
    } catch (error) {
      console.error('Failed to delete doctor:', error);
    }
  };

  const handleCreatePortalAccount = async (email: string) => {
    const password = prompt('Enter initial password for the portal account:');
    if (!password) return;

    try {
      await adminApi.post(`/doctors/${email}/portal-account`, { password });
      fetchData();
      alert('Portal account created successfully');
    } catch (error) {
      console.error('Failed to create portal account:', error);
      alert('Failed to create portal account');
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
          onClick={() => {
            setEditingDoctor(null);
            resetForm();
            setShowModal(true);
          }}
        >
          Add Doctor
        </button>
      </div>

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
                <th>Portal</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {doctors.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-500">
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
                      {doctor.has_portal_account ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-700">
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
                      <button
                        className="btn btn-danger"
                        onClick={() => handleDelete(doctor.email)}
                      >
                        Delete
                      </button>
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
                    <option value="in-person">In-Person</option>
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
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingDoctor ? 'Update' : 'Create'}
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
