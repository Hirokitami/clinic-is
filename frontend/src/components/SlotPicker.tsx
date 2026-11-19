"use client";

import { useState } from "react";
import { Alert, Button, cx, Field, Input, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { addDays, ruDate, todayIso, WEEKDAYS_SHORT } from "@/lib/format";
import type { DaySchedule, Doctor, Nearest, Slot, Specialty } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

export type Picked = { slot: Slot; doctor: Doctor };

/**
 * Блок «Врач и дата приёма» формы записи: специальность → врач → дата → интервалы
 * (свободен / занят / время прошло), «Ближайшие свободные» (А2), «врач не принимает» (И4).
 */
export function SlotPicker({
  fixedDoctor,
  initialDate,
  selected,
  onSelect,
  refreshKey = 0,
  excludeSlotId,
}: {
  fixedDoctor?: Doctor;
  initialDate?: string;
  selected: Slot | null;
  onSelect: (p: Picked | null) => void;
  refreshKey?: number;
  excludeSlotId?: string;
}) {
  const [spec, setSpec] = useState(fixedDoctor?.specialty_code ?? "");
  const [tabState, setTab] = useState(fixedDoctor?.tab_no ?? "");
  const [day, setDay] = useState(initialDate ?? todayIso());
  const [showNearest, setShowNearest] = useState(false);

  const specs = useLoad(() => (fixedDoctor ? null : api.get<Specialty[]>("/refs/specialties")), [fixedDoctor]);
  const doctors = useLoad(
    () => (fixedDoctor || !spec ? null : api.get<Doctor[]>("/schedule/doctors", { specialty: spec })),
    [spec, fixedDoctor],
  );
  // единственный врач специальности выбирается сразу
  const tab = tabState || (!fixedDoctor && doctors.data?.length === 1 ? doctors.data[0].tab_no : "");
  const sched = useLoad(
    () => (tab && day ? api.get<DaySchedule>(`/schedule/${tab}`, { on: day }) : null),
    [tab, day, refreshKey],
  );
  const nearest = useLoad(
    () => (tab && showNearest ? api.get<Nearest>(`/schedule/${tab}/nearest`) : null),
    [tab, showNearest, refreshKey],
  );

  const doctor = fixedDoctor ?? sched.data?.doctor ?? doctors.data?.find((d) => d.tab_no === tab);
  const slots = sched.data?.slots ?? [];
  const noFree = sched.data?.works && !slots.some((s) => s.bookable && s.slot_id !== excludeSlotId);

  function pickDay(d: string, t?: string) {
    if (t && t !== tab) setTab(t);
    setDay(d);
    onSelect(null);
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        {!fixedDoctor && (
          <>
            <Field label="Специальность" required>
              <Select
                value={spec}
                onChange={(e) => {
                  setSpec(e.target.value);
                  setTab("");
                  setShowNearest(false);
                  onSelect(null);
                }}
              >
                <option value="">— выберите —</option>
                {specs.data?.map((s) => (
                  <option key={s.specialty_code} value={s.specialty_code}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Врач" required>
              <Select
                value={tab}
                disabled={!spec}
                onChange={(e) => {
                  setTab(e.target.value);
                  setShowNearest(false);
                  onSelect(null);
                }}
              >
                <option value="">— выберите —</option>
                {doctors.data?.map((d) => (
                  <option key={d.tab_no} value={d.tab_no}>
                    {d.fio}
                  </option>
                ))}
              </Select>
            </Field>
          </>
        )}
        <Field label="Дата приёма" required>
          <div className="flex gap-1">
            <Button variant="secondary" size="sm" aria-label="Предыдущий день" onClick={() => pickDay(addDays(day, -1))}>
              ‹
            </Button>
            <Input type="date" value={day} min={todayIso()} onChange={(e) => pickDay(e.target.value)} />
            <Button variant="secondary" size="sm" aria-label="Следующий день" onClick={() => pickDay(addDays(day, 1))}>
              ›
            </Button>
          </div>
        </Field>
      </div>

      {doctor && (
        <p className="text-sm text-slate-600">
          {doctor.specialty_name} · каб. {doctor.cabinet_no} ({doctor.floor_no} этаж)
          {sched.data && sched.data.work_days.length > 0 && (
            <> · приёмные дни: {sched.data.work_days.map((w) => WEEKDAYS_SHORT[w]).join(", ")}</>
          )}
        </p>
      )}

      {tab && sched.loading && <Spinner />}
      {sched.error && <Alert kind="error">{sched.error.message}</Alert>}
      {sched.data && !sched.data.works && (
        <Alert kind="warn">
          Врач не принимает {ruDate(day, true)}. Выберите другую дату или нажмите «Ближайшие свободные».
        </Alert>
      )}
      {noFree && <Alert kind="warn">На выбранную дату свободных интервалов нет. Нажмите «Ближайшие свободные».</Alert>}

      {sched.data?.works && (
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1"><i className="h-3 w-3 rounded border border-teal-600 bg-white" /> свободен</span>
            <span className="flex items-center gap-1"><i className="h-3 w-3 rounded bg-slate-300" /> занят</span>
            <span className="flex items-center gap-1"><i className="h-3 w-3 rounded bg-slate-100" /> время прошло</span>
          </div>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 lg:grid-cols-8">
            {slots.map((s) => {
              const current = s.slot_id === excludeSlotId;
              const can = s.bookable && !current;
              const isSel = selected?.slot_id === s.slot_id;
              return (
                <button
                  key={s.slot_id}
                  type="button"
                  disabled={!can}
                  onClick={() => doctor && onSelect({ slot: s, doctor })}
                  title={current ? "Текущее время записи" : s.state === "busy" ? "Занят" : s.state === "past" ? "Время прошло" : "Свободен"}
                  className={cx(
                    "rounded-lg px-2 py-2 text-sm font-medium tabular-nums transition",
                    isSel && "bg-teal-700 text-white ring-2 ring-teal-700 ring-offset-1",
                    !isSel && can && "border border-teal-600 bg-white text-teal-800 hover:bg-teal-50",
                    !can && s.state === "busy" && "bg-slate-300 text-slate-600 line-through",
                    !can && s.state !== "busy" && !current && "bg-slate-100 text-slate-400",
                    current && "bg-amber-100 text-amber-900 ring-1 ring-amber-400",
                  )}
                >
                  {s.time_start}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {tab && (
        <div>
          <Button variant="ghost" size="sm" onClick={() => setShowNearest((v) => !v)}>
            {showNearest ? "Скрыть ближайшие свободные" : "Ближайшие свободные"}
          </Button>
          {showNearest && nearest.loading && <Spinner />}
          {showNearest && nearest.data && (
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              <NearestList title={doctor?.fio ?? "Этот врач"} days={nearest.data.doctor} onPick={(d) => pickDay(d)} />
              {!fixedDoctor &&
                nearest.data.same_specialty.map((o) => (
                  <NearestList key={o.tab_no} title={o.name} days={o.days} onPick={(d) => pickDay(d, o.tab_no)} />
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function NearestList({ title, days, onPick }: { title: string; days: Nearest["doctor"]; onPick: (d: string) => void }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="mb-2 text-sm font-medium text-slate-800">{title}</div>
      {days.length === 0 ? (
        <p className="text-sm text-slate-500">Свободных интервалов нет</p>
      ) : (
        <ul className="space-y-1">
          {days.map((d) => (
            <li key={d.date}>
              <button className="w-full rounded px-2 py-1 text-left text-sm hover:bg-teal-50" onClick={() => onPick(d.date)}>
                <span className="font-medium">{ruDate(d.date, true)}</span>
                <span className="text-slate-500"> · с {d.first_time}, свободно {d.free_count}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
