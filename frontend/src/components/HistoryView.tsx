"use client";

import { Badge, Card, Empty, Table, Td } from "@/components/ui";
import { dmy, FIELD_NAMES, money } from "@/lib/format";
import type { PatientHistory, Prescription } from "@/lib/types";

/** История пациента: приёмы и диагнозы, назначения, направления, результаты исследований (Т9, Т12). */
export function HistoryView({ h, showServices = true }: { h: PatientHistory; showServices?: boolean }) {
  return (
    <div className="space-y-5">
      <Card title={`Приёмы и диагнозы (${h.visits.length})`}>
        {h.visits.length === 0 ? (
          <Empty>Приёмов ещё не было</Empty>
        ) : (
          <div className="space-y-4">
            {h.visits.map((v) => (
              <article key={v.visit_no} className="rounded-lg border border-slate-200 p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div className="font-medium text-slate-900">
                    {dmy(v.date)} · {v.specialty_name} {v.doctor_name}
                  </div>
                  <span className="text-xs text-slate-500">{v.visit_no}</span>
                </div>
                <div className="mt-2 text-sm">
                  <Badge className="mr-2 bg-teal-100 font-mono text-teal-900">{v.icd_code}</Badge>
                  {v.diagnosis_name}
                </div>
                <p className="mt-2 text-sm text-slate-700">
                  <span className="text-slate-500">Жалобы: </span>
                  {v.complaints}
                </p>
                {v.conclusion && (
                  <p className="mt-1 text-sm text-slate-700">
                    <span className="text-slate-500">Заключение: </span>
                    {v.conclusion}
                  </p>
                )}
                {showServices && v.services.length > 0 && (
                  <p className="mt-2 text-xs text-slate-500">
                    Услуги: {v.services.map((s) => `${s.service_name}${s.qty > 1 ? ` ×${s.qty}` : ""}`).join(", ")} ·{" "}
                    {money(v.services_total)}
                  </p>
                )}
                {v.changes.length > 0 && (
                  <details className="mt-2 text-xs text-slate-600">
                    <summary className="cursor-pointer">Изменения ({v.changes.length})</summary>
                    <ul className="mt-1 space-y-0.5">
                      {v.changes.map((c, i) => (
                        <li key={i}>
                          {dmy(c.changed_at)} · {c.changed_by}: {FIELD_NAMES[c.field] ?? c.field} «{c.old_value ?? "—"}» →
                          «{c.new_value ?? "—"}»
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </article>
            ))}
          </div>
        )}
      </Card>

      <Card title={`Назначения (${h.prescriptions.length})`}>
        {h.prescriptions.length === 0 ? <Empty>Назначений нет</Empty> : <RxTable rows={h.prescriptions} />}
      </Card>

      <Card title={`Направления и результаты исследований`}>
        {h.referrals.filter((r) => r.status === "ORDERED").length > 0 && (
          <div className="mb-4">
            <h3 className="mb-2 text-sm font-medium text-slate-700">Ожидают выполнения</h3>
            <ul className="space-y-1 text-sm">
              {h.referrals
                .filter((r) => r.status === "ORDERED")
                .map((r) => (
                  <li key={r.ref_no}>
                    <Badge className="mr-2 bg-amber-100 text-amber-900">направление</Badge>
                    {r.test_name} · от {dmy(r.created_at)}, готовность ориентировочно {dmy(r.ready_by)}
                    {r.note && <span className="text-slate-500"> · {r.note}</span>}
                  </li>
                ))}
            </ul>
          </div>
        )}
        {h.tests.length === 0 ? (
          <Empty>Результатов исследований нет</Empty>
        ) : (
          <Table head={["Дата", "Исследование", "Результат"]}>
            {h.tests.map((t) => (
              <tr key={t.result_no}>
                <Td className="whitespace-nowrap">{dmy(t.done_date)}</Td>
                <Td>
                  {t.test_name}
                  <div className="text-xs text-slate-500">{t.test_group}</div>
                </Td>
                <Td>{t.value_text}</Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}

export function RxTable({ rows }: { rows: Prescription[] }) {
  return (
    <Table head={["Назначено", "Процедура", "Сеансы", "Указания", "Выполнение"]}>
      {rows.map((r) => (
        <tr key={r.rx_no}>
          <Td className="whitespace-nowrap">{dmy(r.created_at)}</Td>
          <Td>{r.procedure_name}</Td>
          <Td>
            <span className={r.done_count >= r.sessions ? "text-emerald-700" : ""}>
              {r.done_count} из {r.sessions}
            </span>
          </Td>
          <Td>{r.instructions}</Td>
          <Td className="text-xs text-slate-600">
            {r.executions.length === 0
              ? "—"
              : r.executions.map((e, i) => (
                  <div key={i}>
                    {dmy(e.executed_at)} {e.note && `· ${e.note}`}
                  </div>
                ))}
          </Td>
        </tr>
      ))}
    </Table>
  );
}
