export type Role = "OPERATOR" | "DOCTOR" | "NURSE" | "PATIENT" | "LAB" | "ADMIN";

export type User = {
  login: string;
  role_code: Role;
  role_name: string;
  display_name: string;
  tab_no: string | null;
  iin: string | null;
};

export type Specialty = { specialty_code: string; name: string; visit_minutes: number };

export type Doctor = {
  tab_no: string;
  fio: string;
  short_name: string;
  specialty_code: string;
  specialty_name: string;
  cabinet_no: string;
  floor_no: number;
  work_phone: string | null;
  is_active: boolean;
};

export type RefItem = { code: string; name: string; extra: Record<string, unknown> };

export type Patient = {
  iin: string;
  last_name: string;
  first_name: string;
  middle_name: string | null;
  fio: string;
  birth_date: string;
  sex: "М" | "Ж" | null;
  mobile_phone: string;
  address: string | null;
  doc_type: string | null;
  doc_no: string | null;
  reg_date: string | null;
};

export type Slot = {
  slot_id: string;
  date: string;
  time_start: string;
  time_end: string;
  cabinet_no: string;
  floor_no: number;
  is_busy: boolean;
  bookable: boolean;
  state: "free" | "busy" | "past";
};

export type DaySchedule = { doctor: Doctor; date: string; works: boolean; work_days: number[]; slots: Slot[] };

export type NearestDay = { date: string; free_count: number; first_time: string };
export type Nearest = {
  doctor: NearestDay[];
  same_specialty: { tab_no: string; name: string; days: NearestDay[] }[];
};

export type StatusCode = "PLANNED" | "DONE" | "CANCELLED" | "NO_SHOW";

export type HistoryItem = {
  action: string;
  old_date: string | null;
  old_time: string | null;
  new_date: string | null;
  new_time: string | null;
  old_status: string | null;
  new_status: string | null;
  changed_at: string;
  changed_by: string;
};

export type Appointment = {
  appt_no: string;
  status_code: StatusCode;
  status_name: string;
  reason: string;
  created_at: string;
  created_by: string;
  slot_id: string;
  date: string;
  time_start: string;
  time_end: string;
  cabinet_no: string;
  floor_no: number;
  doctor: Doctor;
  patient_iin: string;
  patient_fio: string;
  patient_birth_date: string;
  patient_phone: string;
  history: HistoryItem[] | null;
};

export type Sms = { id: number; appt_no: string; phone: string; text: string; created_at: string; status: string };

export type AppointmentResult = { appointment: Appointment; sms: Sms | null; message: string };

export type Execution = { executed_at: string; nurse_login: string; note: string | null };

export type Prescription = {
  rx_no: string;
  visit_no: string;
  procedure_code: string;
  procedure_name: string;
  cabinet_no: string | null;
  sessions: number;
  done_count: number;
  instructions: string | null;
  start_date: string;
  created_at: string;
  author: string;
  executions: Execution[];
};

export type Referral = {
  ref_no: string;
  visit_no: string;
  test_code: string;
  test_name: string;
  test_group: string;
  note: string | null;
  status: "ORDERED" | "DONE";
  created_at: string;
  author: string;
  patient_iin: string;
  patient_fio: string;
  doctor_name: string;
  ready_by: string;
};

export type ServiceLine = {
  line_no: string;
  service_code: string;
  service_name: string;
  qty: number;
  price_kzt: number;
  amount_kzt: number;
};

export type VisitChange = {
  field: string;
  old_value: string | null;
  new_value: string | null;
  changed_at: string;
  changed_by: string;
};

export type Visit = {
  visit_no: string;
  appt_no: string;
  date: string;
  complaints: string;
  icd_code: string;
  diagnosis_name: string;
  conclusion: string | null;
  finished_at: string;
  author: string;
  doctor_name: string;
  specialty_name: string;
  tab_no: string;
  prescriptions: Prescription[];
  referrals: Referral[];
  services: ServiceLine[];
  services_total: number;
  changes: VisitChange[];
};

export type TestResult = {
  result_no: string;
  test_code: string;
  test_name: string;
  test_group: string;
  done_date: string;
  value_text: string;
  referral_no: string | null;
};

export type PatientHistory = {
  patient: Patient;
  visits: Visit[];
  prescriptions: Prescription[];
  referrals: Referral[];
  tests: TestResult[];
};

export type DoctorDayRow = { slot: Slot; appointment: Appointment | null; visit_no: string | null };

export type NurseRow = {
  prescription: Prescription;
  patient_iin: string;
  patient_fio: string;
  doctor_name: string;
  done_today: number;
  done_before: number;
  remaining: number;
  state: "todo" | "done_today" | "completed";
};

export type WorkRule = { weekday: number; time_start: string; time_end: string };
export type WorkRules = { doctor: Doctor; rules: WorkRule[]; slots_from: string | null; slots_to: string | null };
