"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Alert, Button, Card, Empty, Field, Input, PageHeader, Select, Spinner, StatusBadge, Table, Td } from "@/components/ui";
import { api } from "@/lib/api";
import { addDays, ruDate, todayIso } from "@/lib/format";
import type { Appointment, Doctor, RefItem } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

/** Список записей с отбором по дате, врачу, пациенту и статусу; переход к переносу и отмене. */
export default function AppointmentsView() {
  const sp = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const on = sp.get("on") ?? todayIso();
  const tab = sp.get("tab_no") ?? "";
  const iin = sp.get("iin") ?? "";
  const status = sp.get("status") ?? "";
  const [iinInput, setIinInput] = useState(iin);

  const doctors = useLoad(() => api.get<Doctor[]>("/schedule/doctors"), []);
  const statuses = useLoad(() => api.get<RefItem[]>("/refs/statuses"), []);
  const rows = useLoad(
    () => api.get<Appointment[]>("/appointments", { on: iin ? undefined : on, tab_no: tab, iin, status }),
    [on, tab, iin, status],
  );

  function setQ(patch: Record<string, string>) {
    const q = new URLSearchParams({ on, tab_no: tab, iin, status, ...patch });
    for (const [k, v] of [...q.entries()]) if (!v) q.delete(k);
    router.replace(`${path}?${q.toString()}`);
  }

  return (
    <>
      <PageHeader title="Список записей" subtitle={iin ? `Все записи пациента ИИН ${iin}` : ruDate(on, true)} />
      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Дата" className="w-auto">
            <div className="flex gap-1">
              <Button size="sm" variant="secondary" onClick={() => setQ({ on: addDays(on, -1), iin: "" })} aria-label="Предыдущий день">‹</Button>
              <Input type="date" value={on} disabled={!!iin} onChange={(e) => setQ({ on: e.target.value })} />
              <Button size="sm" variant="secondary" onClick={() => setQ({ on: addDays(on, 1), iin: "" })} aria-label="Следующий день">›</Button>
            </div>
          </Field>
          <Field label="Врач" className="w-64">
            <Select value={tab} onChange={(e) => setQ({ tab_no: e.target.value })}>
              <option value="">Все врачи</option>
              {doctors.data?.map((d) => (
                <option key={d.tab_no} value={d.tab_no}>
                  {d.fio} ({d.specialty_name})
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Статус" className="w-44">
            <Select value={status} onChange={(e) => setQ({ status: e.target.value })}>
              <option value="">Все</option>
              {statuses.data?.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          <form
            className="flex items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setQ({ iin: iinInput.trim() });
            }}
          >
            <Field label="ИИН пациента" className="w-44">
              <Input value={iinInput} maxLength={12} onChange={(e) => setIinInput(e.target.value.replace(/\D/g, ""))} />
            </Field>
            <Button type="submit" variant="secondary">
              Найти
            </Button>
            {iin && (
              <Button variant="ghost" onClick={() => { setIinInput(""); setQ({ iin: "" }); }}>
                Сбросить
              </Button>
            )}
          </form>
        </div>
      </Card>

      <Card>
        {rows.loading ? (
          <Spinner />
        ) : rows.error ? (
          <Alert kind="error">{rows.error.message}</Alert>
        ) : !rows.data?.length ? (
          <Empty>Записей не найдено</Empty>
        ) : (
          <Table head={["Дата, время", "Пациент", "Врач", "Каб.", "Причина", "Статус", ""]}>
            {rows.data.map((a) => (
              <tr key={a.appt_no} className="hover:bg-slate-50">
                <Td className="whitespace-nowrap tabular-nums">
                  {iin && <div className="text-xs text-slate-500">{ruDate(a.date)}</div>}
                  {a.time_start}
                </Td>
                <Td>
                  {a.patient_fio}
                  <div className="text-xs text-slate-500">ИИН {a.patient_iin}</div>
                </Td>
                <Td>
                  {a.doctor.short_name}
                  <div className="text-xs text-slate-500">{a.doctor.specialty_name}</div>
                </Td>
                <Td>{a.cabinet_no}</Td>
                <Td className="max-w-56 truncate">{a.reason}</Td>
                <Td>
                  <StatusBadge code={a.status_code} name={a.status_name} />
                </Td>
                <Td className="whitespace-nowrap text-right">
                  <Link className="font-medium text-teal-800 hover:underline" href={`/registry/appointments/${a.appt_no}`}>
                    {a.status_code === "PLANNED" ? "Перенос / отмена" : "Открыть"}
                  </Link>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
