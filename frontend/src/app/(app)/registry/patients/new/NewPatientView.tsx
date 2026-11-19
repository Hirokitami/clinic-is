"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { PatientForm } from "@/components/PatientForm";
import { Card, PageHeader } from "@/components/ui";

/** Регистрация пациента (С4). После регистрации из окна записи – возврат к записи с подставленным пациентом (И3). */
export default function NewPatientView() {
  const params = useSearchParams();
  const router = useRouter();
  const ret = params.get("return");

  return (
    <>
      <PageHeader title="Регистрация пациента" subtitle="Создание электронной карты. Поля, отмеченные *, обязательны." />
      <Card>
        <PatientForm
          initialIin={params.get("iin") ?? ""}
          onSaved={(p) => {
            if (ret === "/registry/booking") router.push(`/registry/booking?iin=${p.iin}`);
            else router.push(`/registry/patients/${p.iin}?created=1`);
          }}
        />
      </Card>
    </>
  );
}
