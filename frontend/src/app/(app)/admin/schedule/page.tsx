"use client";

import { useState } from "react";
import { RoleGate } from "@/components/AppShell";
import { Alert, Button, Card, Field, Input, Msg, PageHeader, Select, Spinner, type Message } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { addDays, dmy, todayIso, WEEKDAYS_FULL } from "@/lib/format";
import type { WorkRule, WorkRules } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

/** Рабочее время врачей и формирование расписания (функция 6, перспектива 5 СРО 15). */
export default function SchedulePage() {
  const { data, loading, error, reload } = useLoad(() => api.get<WorkRules[]>("/schedule/work-rules"), []);
  const [msg, setMsg] = useState<Message>(null);
  const [gen, setGen] = useState({ tab_no: "", date_from: todayIso(), date_to: addDays(todayIso(), 28) });

  async function generate() {
    setMsg(null);
    try {
      const r = await api.post<{ message: string }>("/schedule/generate", { ...gen, tab_no: gen.tab_no || null });
      setMsg({ kind: "ok", text: r.message });
      reload();
    } catch (e) {
      setMsg({ kind: "error", text: (e as ApiError).message });
    }
  }

  return (
    <RoleGate roles={["ADMIN"]}>
      <PageHeader title="Расписание врачей" subtitle="Рабочее время по дням недели и формирование интервалов приёма" />
      <Card title="Формирование расписания" className="mb-5">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Врач" className="w-64">
            <Select value={gen.tab_no} onChange={(e) => setGen({ ...gen, tab_no: e.target.value })}>
              <option value="">Все врачи</option>
              {data?.map((w) => (
                <option key={w.doctor.tab_no} value={w.doctor.tab_no}>
                  {w.doctor.fio}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="С">
            <Input type="date" value={gen.date_from} onChange={(e) => setGen({ ...gen, date_from: e.target.value })} />
          </Field>
          <Field label="По">
            <Input type="date" value={gen.date_to} onChange={(e) => setGen({ ...gen, date_to: e.target.value })} />
          </Field>
          <Button onClick={generate}>Сформировать</Button>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Рабочее время нарезается на интервалы длительностью приёма специальности. Дни, на которые расписание уже есть,
          не изменяются – существующие записи пациентов не затрагиваются.
        </p>
        <Msg m={msg} className="mt-3" />
      </Card>
      {loading ? (
        <Spinner />
      ) : error ? (
        <Alert kind="error">{error.message}</Alert>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          {data?.map((w) => <DoctorRules key={w.doctor.tab_no} w={w} onSaved={reload} />)}
        </div>
      )}
    </RoleGate>
  );
}

function DoctorRules({ w, onSaved }: { w: WorkRules; onSaved: () => void }) {
  const [rules, setRules] = useState<Record<number, WorkRule | undefined>>(() =>
    Object.fromEntries(w.rules.map((r) => [r.weekday, r])),
  );
  const [msg, setMsg] = useState<Message>(null);

  async function save() {
    try {
      await api.put(`/schedule/work-rules/${w.doctor.tab_no}`, { rules: Object.values(rules).filter(Boolean) });
      setMsg({ kind: "ok", text: "Рабочее время сохранено" });
      onSaved();
    } catch (e) {
      setMsg({ kind: "error", text: (e as ApiError).message });
    }
  }

  return (
    <Card
      title={
        <span>
          {w.doctor.fio} <span className="font-normal text-slate-500">· {w.doctor.specialty_name}, каб. {w.doctor.cabinet_no}</span>
        </span>
      }
    >
      <div className="space-y-1.5">
        {WEEKDAYS_FULL.map((name, wd) => {
          const r = rules[wd];
          return (
            <div key={wd} className="grid grid-cols-[130px_1fr] items-center gap-2 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-teal-700"
                  checked={!!r}
                  onChange={(e) =>
                    setRules({ ...rules, [wd]: e.target.checked ? { weekday: wd, time_start: "09:00", time_end: "13:00" } : undefined })
                  }
                />
                {name}
              </label>
              {r ? (
                <div className="flex items-center gap-2">
                  <Input type="time" value={r.time_start} className="w-28 py-1" onChange={(e) => setRules({ ...rules, [wd]: { ...r, time_start: e.target.value } })} />
                  –
                  <Input type="time" value={r.time_end} className="w-28 py-1" onChange={(e) => setRules({ ...rules, [wd]: { ...r, time_end: e.target.value } })} />
                </div>
              ) : (
                <span className="text-slate-400">не принимает</span>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button size="sm" onClick={save}>
          Сохранить
        </Button>
        <span className="text-xs text-slate-500">
          {w.slots_from ? `Расписание сформировано: ${dmy(w.slots_from)} – ${dmy(w.slots_to)}` : "Расписание не сформировано"}
        </span>
      </div>
      <Msg m={msg} className="mt-3" />
    </Card>
  );
}
