export type DoctorProfile = {
  email: string;
  name: string;
  specialization: string;
  experience_years: number;
  languages: string[];
  consultation_type: string;
  timezone: string;
};

export type PatientSummary = {
  id: string;
  name: string;
  mobile_number?: string;
  email?: string;
};

export type PatientHistoryItem = {
  id: string;
  created_at: string;
  symptoms?: string;
  medical_conditions?: string[];
  allergies?: string[];
  notes?: string;
};

export type PatientDetail = PatientSummary & {
  gender?: string;
  date_of_birth?: string;
  history: PatientHistoryItem[];
};

export type AppointmentItem = {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  status: string;
  timezone: string;
  patient: PatientSummary;
};
