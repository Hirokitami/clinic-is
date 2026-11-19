"use client";

import { useRouter } from "next/navigation";
import { RoleGate } from "@/components/AppShell";
import { PatientFinder } from "@/components/PatientFinder";
import { Card, LinkButton, PageHeader } from "@/components/ui";

export default function PatientsPage() {
  const router = useRouter();
  return (
    <RoleGate roles={["OPERATOR"]}>
      <PageHeader
        title="Пациенты"
        subtitle="Поиск электронной карты по ИИН или по ФИО и дате рождения"
        actions={
          <LinkButton href="/registry/patients/new" variant="primary">
            Регистрация пациента
          </LinkButton>
        }
      />
      <Card>
        <PatientFinder onPick={(p) => router.push(`/registry/patients/${p.iin}`)} pickLabel="Открыть карту" />
      </Card>
    </RoleGate>
  );
}
