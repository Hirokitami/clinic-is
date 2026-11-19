"use client";

import { useSearchParams } from "next/navigation";
import { BookingForm } from "@/components/BookingForm";
import { PatientFinder } from "@/components/PatientFinder";
import { Button, Card, Dl, LinkButton, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { dmy } from "@/lib/format";
import type { Patient } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";
import { useRouter } from "next/navigation";

/** Окно «Запись на приём» (СРО 11): пациент → врач и дата → интервал и причина обращения. */
export default function BookingView() {
  const params = useSearchParams();
  const router = useRouter();
  const iin = params.get("iin");
  const { data: patient, loading } = useLoad(() => (iin ? api.get<Patient>(`/patients/${iin}`) : null), [iin]);

  function pick(p: Patient | null) {
    router.replace(p ? `/registry/booking?iin=${p.iin}` : "/registry/booking");
  }

  return (
    <>
      <PageHeader title="Запись на приём" subtitle="Регистратура: запись пациента к врачу на свободный интервал" />
      <div className="space-y-5">
        <Card
          title="Пациент"
          actions={
            patient && (
              <>
                <LinkButton size="sm" href={`/registry/patients/${patient.iin}`}>
                  Карта пациента
                </LinkButton>
                <Button size="sm" variant="secondary" onClick={() => pick(null)}>
                  Другой пациент
                </Button>
              </>
            )
          }
        >
          {loading && iin ? (
            <Spinner />
          ) : patient ? (
            <Dl
              items={[
                ["ФИО", patient.fio],
                ["ИИН", patient.iin],
                ["Дата рождения", dmy(patient.birth_date)],
                ["Мобильный телефон", patient.mobile_phone],
              ]}
            />
          ) : (
            <PatientFinder onPick={pick} pickLabel="Выбрать" returnTo="/registry/booking" />
          )}
        </Card>
        {patient && <BookingForm key={patient.iin} patient={patient} mode="operator" rescheduleBase="/registry/appointments" />}
      </div>
    </>
  );
}
