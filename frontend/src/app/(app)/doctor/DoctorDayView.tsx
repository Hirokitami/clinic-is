"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Dialog,
  Empty,
  Input,
  LinkButton,
  Msg,
  PageHeader,
  Spinner,
  StatusBadge,
  Table,
  Td,
  type Message,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { addDays, age, ruDate, todayIso } from "@/lib/format";
import type { Appointment, DoctorDayRow } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

/** Окно 2 «Пациенты на приём» (СРО 13): интервалы дня, история, начать приём, неявка. */
export default function DoctorDayView() {
  const sp = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const on = sp.get("on") ?? todayIso();
  const rows = useLoad(() => api.get<DoctorDayRow[]>("/doctor/day", { on }), [on]);
  const [noShow, setNoShow] = useState<Appointment | null>(null);
  const [msg, setMsg] = useState<Message>(sp.get("saved") ? { kind: "ok", text: "Результаты приёма сохранены. Запись переведена в состояние «Проведена»." } : null);

  const setDay = (d: string) => router.replace(`${path}?on=${d}`);

  async function confirmNoShow() {
    if (!noShow) return;
    try {
      await api.post(`/doctor/appointments/${noShow.appt_no}/no-show`);
      setMsg({ kind: "ok", text: `Отмечена неявка пациента ${noShow.patient_fio} (${noShow.appt_no})` });
      rows.reload();
    } catch (e) {
      setMsg({ kind: "error", text: (e as ApiError).message });
    } finally {
      setNoShow(null);
    }
  }

  const booked = rows.data?.filter((r) => r.appointment).length ?? 0;

  return (
    <>
      <PageHeader
        title="Пациенты на приём"
        subtitle={`${ruDate(on, true)} · записано: ${booked}`}
        actions={
          <div className="flex gap-1">
            <Button variant="secondary" onClick={() => setDay(addDays(on, -1))} aria-label="Предыдущий день">‹</Button>
            <Input type="date" value={on} onChange={(e) => setDay(e.target.value)} className="w-40" />
            <Button variant="secondary" onClick={() => setDay(addDays(on, 1))} aria-label="Следующий день">›</Button>
            <Button variant="ghost" onClick={() => setDay(todayIso())}>Сегодня</Button>
          </div>
        }
      />
      <Msg m={msg} className="mb-5" />
      <Card>
        {rows.loading ? (
          <Spinner />
        ) : rows.error ? (
          <Alert kind="error">{rows.error.message}</Alert>
        ) : !rows.data?.length ? (
          <Empty>В этот день приёма нет</Empty>
        ) : (
          <Table head={["Время", "Пациент", "Причина обращения", "Статус", "Действия"]}>
            {rows.data.map(({ slot, appointment: a, visit_no }) => (
              <tr key={slot.slot_id} className={a ? "" : "text-slate-400"}>
                <Td className="whitespace-nowrap font-medium tabular-nums text-slate-900">
                  {slot.time_start}–{slot.time_end}
                </Td>
                {a ? (
                  <>
                    <Td>
                      <div className="font-medium text-slate-900">{a.patient_fio}</div>
                      <div className="text-xs text-slate-500">
                        {age(a.patient_birth_date)} лет · ИИН {a.patient_iin}
                      </div>
                    </Td>
                    <Td>{a.reason}</Td>
                    <Td>
                      <StatusBadge code={a.status_code} name={a.status_name} />
                    </Td>
                    <Td className="whitespace-nowrap">
                      <div className="flex flex-wrap gap-1.5">
                        <LinkButton size="sm" href={`/doctor/patients/${a.patient_iin}?appt=${a.appt_no}`}>
                          История
                        </LinkButton>
                        {a.status_code === "PLANNED" && (
                          <>
                            <LinkButton size="sm" variant="primary" href={`/doctor/visit/${a.appt_no}`}>
                              Начать приём
                            </LinkButton>
                            <Button size="sm" variant="danger" onClick={() => setNoShow(a)}>
                              Неявка
                            </Button>
                          </>
                        )}
                        {visit_no && (
                          <LinkButton size="sm" variant="ghost" href={`/doctor/visit/${a.appt_no}`}>
                            Результаты приёма
                          </LinkButton>
                        )}
                      </div>
                    </Td>
                  </>
                ) : (
                  <Td colSpan={4}>{slot.state === "past" ? "не использован" : "свободно"}</Td>
                )}
              </tr>
            ))}
          </Table>
        )}
      </Card>

      <Dialog
        open={!!noShow}
        title="Отметить неявку?"
        onClose={() => setNoShow(null)}
        actions={
          <>
            <Button variant="secondary" onClick={() => setNoShow(null)}>
              Отмена
            </Button>
            <Button variant="danger" onClick={confirmNoShow}>
              Подтвердить неявку
            </Button>
          </>
        }
      >
        {noShow && (
          <p>
            Пациент <b>{noShow.patient_fio}</b> не явился на приём {ruDate(noShow.date)} в {noShow.time_start}. Запись
            будет переведена в состояние «Неявка», интервал останется в истории.
          </p>
        )}
      </Dialog>
    </>
  );
}
