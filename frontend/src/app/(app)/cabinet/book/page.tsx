"use client";

import { RoleGate } from "@/components/AppShell";
import { BookingForm } from "@/components/BookingForm";
import { PageHeader } from "@/components/ui";

/** Самостоятельная запись пациента через личный кабинет (С1, функция 22). */
export default function SelfBookingPage() {
  return (
    <RoleGate roles={["PATIENT"]}>
      <PageHeader title="Запись к врачу" subtitle="Выберите специальность, врача, дату и свободное время" />
      <BookingForm patient={null} mode="patient" rescheduleBase="/cabinet/appointments" />
    </RoleGate>
  );
}
