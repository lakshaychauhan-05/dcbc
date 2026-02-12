// Chat types
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  intent?: IntentClassification;
  suggestedActions?: string[];
  metadata?: Record<string, unknown>;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
  user_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  intent?: IntentClassification;
  suggested_actions?: string[];
  requires_confirmation: boolean;
  booking_details?: Record<string, unknown>;
  timestamp: string;
}

export interface IntentClassification {
  intent: IntentType;
  confidence: number;
  entities: ExtractedEntity[];
}

export enum IntentType {
  BOOK_APPOINTMENT = 'book_appointment',
  RESCHEDULE_APPOINTMENT = 'reschedule_appointment',
  CANCEL_APPOINTMENT = 'cancel_appointment',
  GET_DOCTOR_INFO = 'get_doctor_info',
  CHECK_AVAILABILITY = 'check_availability',
  GET_MY_APPOINTMENTS = 'get_my_appointments',
  GENERAL_INFO = 'general_info',
  UNKNOWN = 'unknown',
}

export enum EntityType {
  DATE = 'date',
  TIME = 'time',
  DOCTOR_NAME = 'doctor_name',
  SPECIALIZATION = 'specialization',
  PATIENT_NAME = 'patient_name',
  PHONE_NUMBER = 'phone_number',
  EMAIL = 'email',
  SYMPTOMS = 'symptoms',
}

export interface ExtractedEntity {
  type: EntityType;
  value: string;
  confidence: number;
  start_pos?: number;
  end_pos?: number;
}

// Doctor Portal types
export interface DoctorProfile {
  email: string;
  name: string;
  phone_number?: string;
  specialization: string;
  experience_years: number;
  languages: string[];
  consultation_type: string;
  timezone: string;
}

export interface PatientSummary {
  id: string;
  name: string;
  mobile_number?: string;
  email?: string;
  sms_opt_in?: boolean;
}

export interface PatientHistoryItem {
  id: string;
  created_at: string;
  symptoms?: string;
  medical_conditions?: string[];
  allergies?: string[];
  notes?: string;
}

export interface PatientDetail extends PatientSummary {
  gender?: string;
  date_of_birth?: string;
  history: PatientHistoryItem[];
}

export interface AppointmentItem {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  status: string;
  timezone: string;
  patient: PatientSummary;
  notes?: string;
  source?: string;
  calendar_sync_status?: string;
  created_at?: string;
}

// Admin Portal types
export interface Clinic {
  id: string;
  name: string;
  address?: string;
  phone_number?: string;
  email?: string;
  is_active: boolean;
  created_at: string;
}

export interface Doctor {
  email: string;
  name: string;
  phone_number?: string;
  specialization: string;
  experience_years: number;
  languages: string[];
  consultation_type: string;
  is_active: boolean;
  has_portal_account: boolean;
  clinic_id?: string;
  clinic_name?: string;
}
