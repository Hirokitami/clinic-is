"use client";

import Link from "next/link";
import { useState } from "react";
import { RoleGate } from "@/components/AppShell";
import { HistoryView } from "@/components/HistoryView";
import { Alert, Card, cx, Empty, LinkButton, PageHeader, Spinner, StatusBadge, Table, Td } from "@/components/ui";
import { api } from "@/lib/api";
import { dmy, ruDate } from "@/lib/format";
import type { Appointment, PatientHistory } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

type Cabinet = { appointments: Appointment[]; health: PatientHistory };

/** Личный кабинет пациента: свои записи, результаты, диагнозы, назначения (С2, С3, Т12). */
export default function CabinetPage() {
  const { data, loading, error } = useLoad(() => api.get<Cabinet>("/cabinet"), []);
  const [tab, setTab] = useState<"appts" | "health">("appts");

  return (
    <RoleGate roles={["PATIENT"]}>
      <PageHeader
        title="Личный кабинет"
        subtitle={data ? `${data.health.patient.fio} · ИИН ${data.health.patient.iin}` : ""}
        actions={
          <LinkButton href="/cabinet/book" variant="primary">
            Записаться к врачу
          </LinkButton>
        }
      />
      <div className="mb-5 inline-flex rounded-lg bg-slate-200/60 p-1 text-sm">
        {(
          [
            ["appts", "Мои записи"],
            ["health", "Сведения о здоровье"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={cx("rounded-md px-4 py-1.5", tab === k ? "bg-white font-medium shadow-sm" : "text-slate-600")}
          >
            {label}
          </button>
        ))}
      </div>
      {loading ? (
        <Spinner />
      ) : error || !data ? (
        <Alert kind="error">{error?.message}</Alert>
      ) : tab === "appts" ? (
        <Card>
          {data.appointments.length === 0 ? (
            <Empty>Записей нет</Empty>
          ) : (
            <Table head={["Дата и время", "Врач", "Кабинет", "Причина", "Статус", ""]}>
              {data.appointments.map((a) => (
                <tr key={a.appt_no}>
                  <Td className="whitespace-nowrap">
                    {ruDate(a.date, true)}
                    <div className="text-slate-500">{a.time_start}</div>
                  </Td>
                  <Td>
                    {a.doctor.fio}
                    <div className="text-xs text-slate-500">{a.doctor.specialty_name}</div>
                  </Td>
                  <Td>
                    {a.cabinet_no}
                    <div className="text-xs text-slate-500">{a.floor_no} этаж</div>
                  </Td>
                  <Td>{a.reason}</Td>
                  <Td>
                    <StatusBadge code={a.status_code} name={a.status_name} />
                  </Td>
                  <Td className="whitespace-nowrap text-right">
                    {a.status_code === "PLANNED" ? (
                      <Link className="font-medium text-teal-800 hover:underline" href={`/cabinet/appointments/${a.appt_no}`}>
                        Перенести / отменить
                      </Link>
                    ) : (
                      <span className="text-xs text-slate-400">{dmy(a.created_at).slice(0, 10)}</span>
                    )}
                  </Td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      ) : (
        <HistoryView h={data.health} />
      )}
    </RoleGate>
  );
}
