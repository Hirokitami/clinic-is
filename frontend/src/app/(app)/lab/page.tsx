"use client";

import { Fragment, useState } from "react";
import { RoleGate } from "@/components/AppShell";
import { Alert, Badge, Button, Card, Empty, Input, Msg, PageHeader, Select, Spinner, Table, Td, Textarea, type Message } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { dmy, todayIso } from "@/lib/format";
import type { Referral } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

/** Направления на исследования и внесение результатов сотрудником лаборатории. */
export default function LabPage() {
  const [status, setStatus] = useState("ORDERED");
  const rows = useLoad(() => api.get<Referral[]>("/lab/referrals", { status }), [status]);
  const [open, setOpen] = useState<string | null>(null);
  const [value, setValue] = useState("");
  const [done, setDone] = useState(todayIso());
  const [msg, setMsg] = useState<Message>(null);
  const [err, setErr] = useState("");

  async function save(ref: Referral) {
    setErr("");
    try {
      await api.post(`/lab/referrals/${ref.ref_no}/result`, { value_text: value, done_date: done });
      setMsg({ kind: "ok", text: `Результат «${ref.test_name}» для ${ref.patient_fio} внесён в карту` });
      setOpen(null);
      setValue("");
      rows.reload();
    } catch (e) {
      setErr((e as ApiError).message);
    }
  }

  return (
    <RoleGate roles={["LAB"]}>
      <PageHeader
        title="Направления на исследования"
        actions={
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-56">
            <option value="ORDERED">Ожидают результата</option>
            <option value="DONE">Выполненные</option>
            <option value="">Все</option>
          </Select>
        }
      />
      <Msg m={msg} className="mb-5" />
      <Card>
        {rows.loading ? (
          <Spinner />
        ) : rows.error ? (
          <Alert kind="error">{rows.error.message}</Alert>
        ) : !rows.data?.length ? (
          <Empty>Направлений нет</Empty>
        ) : (
          <Table head={["Направление", "Пациент", "Исследование", "Врач", "Готовность", ""]}>
            {rows.data.map((r) => (
              <Fragment key={r.ref_no}>
                <tr>
                  <Td className="whitespace-nowrap">
                    {r.ref_no}
                    <div className="text-xs text-slate-500">{dmy(r.created_at)}</div>
                  </Td>
                  <Td>
                    {r.patient_fio}
                    <div className="text-xs text-slate-500">ИИН {r.patient_iin}</div>
                  </Td>
                  <Td>
                    {r.test_name}
                    <div className="text-xs text-slate-500">{r.test_group}{r.note && ` · ${r.note}`}</div>
                  </Td>
                  <Td>{r.doctor_name}</Td>
                  <Td className="whitespace-nowrap">{dmy(r.ready_by)}</Td>
                  <Td className="text-right">
                    {r.status === "ORDERED" ? (
                      <Button size="sm" variant={open === r.ref_no ? "secondary" : "primary"} onClick={() => { setOpen(open === r.ref_no ? null : r.ref_no); setErr(""); }}>
                        {open === r.ref_no ? "Свернуть" : "Внести результат"}
                      </Button>
                    ) : (
                      <Badge className="bg-emerald-100 text-emerald-800">результат внесён</Badge>
                    )}
                  </Td>
                </tr>
                {open === r.ref_no && (
                  <tr className="bg-slate-50">
                    <Td colSpan={6}>
                      <div className="grid gap-3 sm:grid-cols-[1fr_180px_auto] sm:items-end">
                        <label className="block text-sm">
                          <span className="mb-1 block font-medium text-slate-700">Результат *</span>
                          <Textarea rows={2} value={value} onChange={(e) => setValue(e.target.value)} invalid={!!err} />
                        </label>
                        <label className="block text-sm">
                          <span className="mb-1 block font-medium text-slate-700">Дата выполнения</span>
                          <Input type="date" value={done} max={todayIso()} onChange={(e) => setDone(e.target.value)} />
                        </label>
                        <Button onClick={() => save(r)}>Сохранить</Button>
                      </div>
                      {err && <p className="mt-2 text-sm text-red-700">{err}</p>}
                    </Td>
                  </tr>
                )}
              </Fragment>
            ))}
          </Table>
        )}
      </Card>
    </RoleGate>
  );
}
