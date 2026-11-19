"use client";

import { useState } from "react";
import { Alert, Badge, Button, Card, Empty, Field, Input, Msg, PageHeader, Select, Spinner, Table, Td, type Message } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { ruDate, todayIso } from "@/lib/format";
import type { NurseRow, RefItem } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

const STATE: Record<NurseRow["state"], [string, string]> = {
  todo: ["к выполнению", "bg-sky-100 text-sky-800"],
  done_today: ["выполнено сегодня", "bg-emerald-100 text-emerald-800"],
  completed: ["курс завершён", "bg-slate-200 text-slate-700"],
};

/** Окно «Процедуры»: отбор по дате, кабинету и состоянию, отметка выполнения (С10, С11). */
export default function NurseView() {
  const [on, setOn] = useState(todayIso());
  const [cabinet, setCabinet] = useState("");
  const [state, setState] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<Message>(null);
  const [busy, setBusy] = useState("");
  const cabinets = useLoad(() => api.get<RefItem[]>("/refs/cabinets"), []);
  const rows = useLoad(() => api.get<NurseRow[]>("/nurse/procedures", { on, cabinet, state }), [on, cabinet, state]);
  const isToday = on === todayIso();

  async function execute(rx: string) {
    setBusy(rx);
    try {
      const r = await api.post<{ message: string }>(`/nurse/prescriptions/${rx}/execute`, { note: notes[rx] ?? "" });
      setMsg({ kind: "ok", text: `${rx}: ${r.message}` });
      setNotes((n) => ({ ...n, [rx]: "" }));
      rows.reload();
    } catch (e) {
      setMsg({ kind: "error", text: (e as ApiError).message });
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageHeader title="Процедуры" subtitle={`Перечень назначенных процедур на ${ruDate(on, true)}`} />
      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Дата" className="w-44">
            <Input type="date" value={on} onChange={(e) => setOn(e.target.value)} />
          </Field>
          <Field label="Кабинет" className="w-64">
            <Select value={cabinet} onChange={(e) => setCabinet(e.target.value)}>
              <option value="">Все кабинеты</option>
              {cabinets.data
                ?.filter((c) => ["105", "108"].includes(c.code))
                .map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code} — {c.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field label="Состояние" className="w-48">
            <Select value={state} onChange={(e) => setState(e.target.value)}>
              <option value="">Все</option>
              <option value="todo">К выполнению</option>
              <option value="done_today">Выполнено сегодня</option>
              <option value="completed">Курс завершён</option>
            </Select>
          </Field>
        </div>
      </Card>
      <Msg m={msg} className="mb-5" />
      <Card>
        {rows.loading ? (
          <Spinner />
        ) : rows.error ? (
          <Alert kind="error">{rows.error.message}</Alert>
        ) : !rows.data?.length ? (
          <Empty>Назначенных процедур нет</Empty>
        ) : (
          <Table head={["Пациент", "Процедура", "Каб.", "Сеансы", "Указания врача", "Состояние", "Отметка"]}>
            {rows.data.map((r) => {
              const p = r.prescription;
              const [label, cls] = STATE[r.state];
              return (
                <tr key={p.rx_no}>
                  <Td>
                    <div className="font-medium">{r.patient_fio}</div>
                    <div className="text-xs text-slate-500">назначил {r.doctor_name}</div>
                  </Td>
                  <Td>
                    {p.procedure_name}
                    <div className="text-xs text-slate-500">{p.rx_no}</div>
                  </Td>
                  <Td>{p.cabinet_no}</Td>
                  <Td className="whitespace-nowrap tabular-nums">
                    {p.done_count} из {p.sessions}
                  </Td>
                  <Td className="max-w-56">{p.instructions}</Td>
                  <Td>
                    <Badge className={cls}>{label}</Badge>
                  </Td>
                  <Td className="min-w-56">
                    {r.remaining > 0 && isToday ? (
                      <div className="flex gap-1.5">
                        <Input
                          placeholder="Примечание"
                          value={notes[p.rx_no] ?? ""}
                          onChange={(e) => setNotes((n) => ({ ...n, [p.rx_no]: e.target.value }))}
                        />
                        <Button size="sm" disabled={busy === p.rx_no} onClick={() => execute(p.rx_no)}>
                          Выполнено
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-500">{r.remaining > 0 ? "отметка – в день выполнения" : "—"}</span>
                    )}
                  </Td>
                </tr>
              );
            })}
          </Table>
        )}
      </Card>
    </>
  );
}
