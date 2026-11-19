"use client";

import { useState } from "react";
import { RoleGate } from "@/components/AppShell";
import { Alert, Card, Empty, Field, Input, PageHeader, Spinner, Table, Td } from "@/components/ui";
import { api } from "@/lib/api";
import { addDays, dmy, money, todayIso } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";

type Report = {
  date_from: string;
  date_to: string;
  totals: Record<string, number>;
  doctors: {
    tab_no: string;
    name: string;
    specialty: string;
    slots: number;
    busy: number;
    load_pct: number;
    planned: number;
    done: number;
    no_show: number;
    cancelled: number;
    no_show_pct: number;
  }[];
  by_specialty: { specialty: string; appointments: number }[];
  by_day: { date: string; appointments: number }[];
  services: { code: string; name: string; qty: number; amount_kzt: number }[];
};

/** Отчёты для главного врача: загрузка врачей, неявки, обращаемость, услуги (перспектива 6 СРО 15). */
export default function ReportsPage() {
  const [from, setFrom] = useState(addDays(todayIso(), -14));
  const [to, setTo] = useState(addDays(todayIso(), 14));
  const { data: r, loading, error } = useLoad(() => api.get<Report>("/reports", { date_from: from, date_to: to }), [from, to]);

  return (
    <RoleGate roles={["ADMIN"]}>
      <PageHeader
        title="Отчёты"
        actions={
          <div className="flex items-end gap-2">
            <Field label="С">
              <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            </Field>
            <Field label="По">
              <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
            </Field>
          </div>
        }
      />
      {loading ? (
        <Spinner />
      ) : error || !r ? (
        <Alert kind="error">{error?.message}</Alert>
      ) : (
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Tile label="Загрузка расписания" value={`${r.totals.load_pct}%`} sub={`${r.totals.busy} из ${r.totals.slots} интервалов`} />
            <Tile label="Проведено приёмов" value={r.totals.done} sub={`запланировано ${r.totals.planned}, отменено ${r.totals.cancelled}`} />
            <Tile label="Доля неявок" value={`${r.totals.no_show_pct}%`} sub={`${r.totals.no_show} неявок`} />
            <Tile label="Оказано услуг на сумму" value={money(r.totals.revenue_kzt)} sub={`новых пациентов: ${r.totals.new_patients}`} />
          </div>

          <Card title="Записи на приём по дням">
            <DayBars days={r.by_day} />
          </Card>

          <Card title="Загрузка врачей">
            <Table head={["Врач", "Интервалов", "Занято", "Загрузка", "Проведено", "Неявки", "Отменено"]}>
              {r.doctors.map((d) => (
                <tr key={d.tab_no}>
                  <Td>
                    {d.name}
                    <div className="text-xs text-slate-500">{d.specialty}</div>
                  </Td>
                  <Td className="tabular-nums">{d.slots}</Td>
                  <Td className="tabular-nums">{d.busy}</Td>
                  <Td className="min-w-48">
                    <div className="flex items-center gap-2">
                      <div className="h-2 flex-1 rounded-full bg-slate-100" role="meter" aria-valuenow={d.load_pct} aria-valuemin={0} aria-valuemax={100} aria-label={`Загрузка ${d.name}`}>
                        <div className="h-2 rounded-full bg-teal-600" style={{ width: `${Math.min(d.load_pct, 100)}%` }} />
                      </div>
                      <span className="w-12 text-right tabular-nums text-slate-700">{d.load_pct}%</span>
                    </div>
                  </Td>
                  <Td className="tabular-nums">{d.done}</Td>
                  <Td className="tabular-nums">
                    {d.no_show} {d.no_show > 0 && <span className="text-xs text-slate-500">({d.no_show_pct}%)</span>}
                  </Td>
                  <Td className="tabular-nums">{d.cancelled}</Td>
                </tr>
              ))}
            </Table>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Обращаемость по специальностям">
              {r.by_specialty.length === 0 ? (
                <Empty>Нет записей</Empty>
              ) : (
                <Table head={["Специальность", "Записей"]}>
                  {r.by_specialty.map((s) => (
                    <tr key={s.specialty}>
                      <Td>{s.specialty}</Td>
                      <Td className="tabular-nums">{s.appointments}</Td>
                    </tr>
                  ))}
                </Table>
              )}
            </Card>
            <Card title="Оказанные услуги">
              {r.services.length === 0 ? (
                <Empty>Услуг за период нет</Empty>
              ) : (
                <Table head={["Услуга", "Кол-во", "Сумма"]}>
                  {r.services.map((s) => (
                    <tr key={s.code}>
                      <Td>{s.name}</Td>
                      <Td className="tabular-nums">{s.qty}</Td>
                      <Td className="tabular-nums">{money(s.amount_kzt)}</Td>
                    </tr>
                  ))}
                </Table>
              )}
            </Card>
          </div>
        </div>
      )}
    </RoleGate>
  );
}

function Tile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold tabular-nums text-slate-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

/** Одна серия → без легенды; подсказка при наведении; таблица значений – под спойлером. */
function DayBars({ days }: { days: Report["by_day"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...days.map((d) => d.appointments));
  const today = todayIso();
  return (
    <div>
      <div className="relative">
        <div className="flex h-40 items-end gap-[2px] border-b border-slate-300">
          {days.map((d, i) => (
            <div
              key={d.date}
              className="flex h-full flex-1 cursor-default items-end"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            >
              <div
                className={`w-full rounded-t ${d.date === today ? "bg-teal-800" : "bg-teal-500"} ${hover === i ? "opacity-80" : ""}`}
                style={{ height: `${(d.appointments / max) * 100}%`, minHeight: d.appointments ? 2 : 0 }}
              />
            </div>
          ))}
        </div>
        {hover !== null && (
          <div
            className="pointer-events-none absolute -top-2 rounded-md bg-slate-900 px-2 py-1 text-xs text-white shadow"
            style={{ left: `${((hover + 0.5) / days.length) * 100}%`, transform: "translate(-50%, -100%)" }}
          >
            {dmy(days[hover].date)}: {days[hover].appointments}
          </div>
        )}
      </div>
      <div className="mt-1 flex justify-between text-xs text-slate-500">
        <span>{dmy(days[0]?.date)}</span>
        <span>макс. {max} в день · тёмный столбец – сегодня</span>
        <span>{dmy(days[days.length - 1]?.date)}</span>
      </div>
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-slate-600">Таблица значений</summary>
        <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-0.5 sm:grid-cols-4">
          {days.map((d) => (
            <div key={d.date} className="flex justify-between tabular-nums">
              <span className="text-slate-500">{dmy(d.date)}</span>
              <span>{d.appointments}</span>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
