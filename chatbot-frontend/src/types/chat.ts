export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  intent?: IntentClassification;
  suggestedActions?: string[];
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
  user_id?: string | null;
  metadata?: Record<string, any>;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  intent?: IntentClassification;
  suggested_actions?: string[];
  requires_confirmation: boolean;
  booking_details?: Record<string, any>;
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

export interface Conversation {
  id: string;
  user_id?: string;
  messages: Message[];
  state: ConversationState;
  context: Record<string, any>;
  created_at: Date;
  updated_at: Date;
  expires_at?: Date;
}

export enum ConversationState {
  INITIAL = 'initial',
  GATHERING_INFO = 'gathering_info',
  CONFIRMING_BOOKING = 'confirming_booking',
  BOOKING_APPOINTMENT = 'booking_appointment',
  COMPLETED = 'completed',
  ERROR = 'error',
}

export interface BookingDetails {
  doctor_email?: string;
  date?: string;
  time?: string;
  patient_name?: string;
  patient_phone?: string;
  patient_email?: string;
  symptoms?: string;
  appointment_type?: string;
}

export interface DoctorInfo {
  email: string;
  name: string;
  specialization: string;
  experience_years: number;
  languages: string[];
  consultation_type: string;
  working_days: string[];
  working_hours: Record<string, string>;
  slot_duration_minutes: number;
  rating?: number;
  patient_reviews?: number;
  expertise_areas?: string[];
}