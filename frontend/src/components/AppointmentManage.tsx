"use client";

import { useState } from "react";
import { SlotPicker, type Picked } from "@/components/SlotPicker";
import {
  Alert,
  Button,
  Card,
  Dialog,
  Dl,
  Empty,
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
import { dmy, ruDate } from "@/lib/format";
import type { Appointment, AppointmentResult } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

/** Карточка записи: сведения, перенос (Т6.1), отмена (Т6.2), история изменений (Т7). */
export function AppointmentManage({ apptNo, backHref, backLabel }: { apptNo: string; backHref: string; backLabel: string }) {
  const { data: a, error, loading, setData } = useLoad(() => api.get<Appointment>(`/appointments/${apptNo}`), [apptNo]);
  const [picked, setPicked] = useState<Picked | null>(null);
  const [msg, setMsg] = useState<Message>(null);
  const [busy, setBusy] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [refresh, setRefresh] = useState(0);

  if (loading) return <Spinner />;
  if (error || !a) return <Alert kind="error">{error?.message ?? "Запись не найдена"}</Alert>;

  const planned = a.status_code === "PLANNED";

  async function act(kind: "reschedule" | "cancel") {
    setBusy(true);
    setMsg(null);
    try {
      const r =
        kind === "reschedule"
          ? await api.post<AppointmentResult>(`/appointments/${apptNo}/reschedule`, { slot_id: picked!.slot.slot_id })
          : await api.post<AppointmentResult>(`/appointments/${apptNo}/cancel`);
      const fresh = await api.get<Appointment>(`/appointments/${apptNo}`);
      setData(fresh);
      setPicked(null);
      setMsg({ kind: "ok", text: <>{r.message}. {r.sms && <span className="block text-xs">SMS: {r.sms.text}</span>}</> });
    } catch (e) {
      setMsg({ kind: "error", text: (e as ApiError).message });
      if ((e as ApiError).code === "SLOT_BUSY") setPicked(null);
    } finally {
      setBusy(false);
      setConfirmCancel(false);
      setRefresh((x) => x + 1);
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title={`Запись ${a.appt_no}`}
        subtitle={<StatusBadge code={a.status_code} name={a.status_name} />}
        actions={
          <>
            <LinkButton href={backHref}>{backLabel}</LinkButton>
            <LinkButton href={`/ticket/${a.appt_no}`}>Талон</LinkButton>
            {planned && (
              <Button variant="danger" onClick={() => setConfirmCancel(true)}>
                Отменить запись
              </Button>
            )}
          </>
        }
      />
      <Msg m={msg} />
      <Card title="Сведения о записи">
        <Dl
          items={[
            ["Пациент", `${a.patient_fio}, ИИН ${a.patient_iin}`],
            ["Врач", `${a.doctor.fio} (${a.doctor.specialty_name})`],
            ["Дата и время", `${ruDate(a.date, true)}, ${a.time_start}–${a.time_end}`],
            ["Кабинет", `${a.cabinet_no}, ${a.floor_no} этаж`],
            ["Причина обращения", a.reason],
            ["Оформлена", `${dmy(a.created_at)} (${a.created_by})`],
          ]}
        />
      </Card>

      {planned && (
        <Card title="Перенос записи">
          <p className="mb-4 text-sm text-slate-600">
            Выберите новый свободный интервал врача. Прежнее время освободится, пациент получит SMS.
          </p>
          <SlotPicker
            fixedDoctor={a.doctor}
            initialDate={a.date}
            selected={picked?.slot ?? null}
            onSelect={setPicked}
            excludeSlotId={a.slot_id}
            refreshKey={refresh}
          />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button disabled={!picked || busy} onClick={() => act("reschedule")}>
              Перенести
            </Button>
            {picked && (
              <span className="text-sm text-slate-700">
                на {ruDate(picked.slot.date, true)}, {picked.slot.time_start}
              </span>
            )}
          </div>
        </Card>
      )}

      <Card title="История изменений">
        {a.history?.length ? (
          <Table head={["Когда", "Действие", "Было", "Стало", "Кто"]}>
            {a.history.map((h, i) => (
              <tr key={i}>
                <Td>{dmy(h.changed_at)}</Td>
                <Td>{h.action}</Td>
                <Td>{h.old_date ? `${dmy(h.old_date)} ${h.old_time}` : h.old_status ?? ""}</Td>
                <Td>{h.new_date ? `${dmy(h.new_date)} ${h.new_time}` : h.new_status ?? ""}</Td>
                <Td>{h.changed_by}</Td>
              </tr>
            ))}
          </Table>
        ) : (
          <Empty>Изменений нет</Empty>
        )}
      </Card>

      <Dialog
        open={confirmCancel}
        title="Отменить запись?"
        onClose={() => setConfirmCancel(false)}
        actions={
          <>
            <Button variant="secondary" onClick={() => setConfirmCancel(false)}>
              Не отменять
            </Button>
            <Button variant="danger" disabled={busy} onClick={() => act("cancel")}>
              Отменить запись
            </Button>
          </>
        }
      >
        Запись {a.appt_no} к врачу {a.doctor.fio} на {ruDate(a.date, true)} в {a.time_start} будет отменена, интервал
        освободится.
      </Dialog>
    </div>
  );
}
