"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { PatientForm } from "@/components/PatientForm";
import { Alert, Card, Empty, LinkButton, PageHeader, Spinner, StatusBadge, Table, Td } from "@/components/ui";
import { api } from "@/lib/api";
import { dmy } from "@/lib/format";
import type { Appointment, Patient } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

export default function PatientCardView() {
  const { iin } = useParams<{ iin: string }>();
  const created = useSearchParams().get("created");
  const p = useLoad(() => api.get<Patient>(`/patients/${iin}`), [iin]);
  const appts = useLoad(() => api.get<Appointment[]>("/appointments", { iin }), [iin]);

  if (p.loading) return <Spinner />;
  if (p.error || !p.data) return <Alert kind="error">{p.error?.message ?? "Пациент не найден"}</Alert>;

  return (
    <>
      <PageHeader
        title={p.data.fio}
        subtitle={`ИИН ${p.data.iin} · карта от ${dmy(p.data.reg_date)}`}
        actions={
          <LinkButton href={`/registry/booking?iin=${p.data.iin}`} variant="primary">
            Записать на приём
          </LinkButton>
        }
      />
      {created && <Alert kind="ok" className="mb-5">Пациент зарегистрирован. Электронная карта создана.</Alert>}
      <div className="space-y-5">
        <Card title="Данные карты">
          <PatientForm key={p.data.iin} patient={p.data} onSaved={(np) => p.setData(np)} />
        </Card>
        <Card title="Записи на приём">
          {appts.loading ? (
            <Spinner />
          ) : !appts.data?.length ? (
            <Empty>Записей нет</Empty>
          ) : (
            <Table head={["Дата", "Время", "Врач", "Кабинет", "Статус", ""]}>
              {appts.data.map((a) => (
                <tr key={a.appt_no}>
                  <Td>{dmy(a.date)}</Td>
                  <Td>{a.time_start}</Td>
                  <Td>
                    {a.doctor.fio}
                    <div className="text-xs text-slate-500">{a.doctor.specialty_name}</div>
                  </Td>
                  <Td>{a.cabinet_no}</Td>
                  <Td>
                    <StatusBadge code={a.status_code} name={a.status_name} />
                  </Td>
                  <Td>
                    <Link className="text-teal-800 hover:underline" href={`/registry/appointments/${a.appt_no}`}>
                      {a.appt_no}
                    </Link>
                  </Td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      </div>
    </>
  );
}
