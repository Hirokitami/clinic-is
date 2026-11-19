"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { RxTable } from "@/components/HistoryView";
import {
  Alert,
  Badge,
  Button,
  Card,
  Dl,
  Empty,
  Field,
  Input,
  LinkButton,
  Msg,
  PageHeader,
  Select,
  Spinner,
  StatusBadge,
  Table,
  Td,
  Textarea,
  type Message,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { age, dmy, FIELD_NAMES, money, ruDate } from "@/lib/format";
import type { Appointment, RefItem, Visit } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

type RxRow = { procedure_code: string; sessions: string; instructions: string };
type RefRow = { test_code: string; note: string };
type SvcRow = { service_code: string; qty: string };

/** Окно 4 «Приём пациента» (СРО 13): результаты приёма, назначения, направления, услуги (Т10). */
export default function VisitView() {
  const { no } = useParams<{ no: string }>();
  const appt = useLoad(() => api.get<Appointment>(`/doctor/appointments/${no}`), [no]);
  const visit = useLoad(() => api.get<Visit | null>(`/doctor/appointments/${no}/visit`), [no]);

  if (appt.loading || visit.loading) return <Spinner />;
  if (appt.error || !appt.data) return <Alert kind="error">{appt.error?.message ?? "Запись не найдена"}</Alert>;
  const a = appt.data;

  return (
    <>
      <PageHeader
        title="Приём пациента"
        subtitle={<StatusBadge code={a.status_code} name={a.status_name} />}
        actions={
          <>
            <LinkButton href={`/doctor?on=${a.date}`}>К списку пациентов</LinkButton>
            <LinkButton href={`/doctor/patients/${a.patient_iin}?appt=${a.appt_no}`}>История пациента</LinkButton>
          </>
        }
      />
      <Card title="Запись" className="mb-5">
        <Dl
          items={[
            ["Пациент", `${a.patient_fio}, ${age(a.patient_birth_date)} лет, ИИН ${a.patient_iin}`],
            ["Дата и время", `${ruDate(a.date, true)}, ${a.time_start}–${a.time_end}, каб. ${a.cabinet_no}`],
            ["Причина обращения", a.reason],
          ]}
        />
      </Card>
      {visit.data ? (
        <VisitResult v={visit.data} onChanged={(v) => visit.setData(v)} />
      ) : a.status_code === "PLANNED" ? (
        <VisitForm a={a} />
      ) : (
        <Alert kind="warn">Запись в состоянии «{a.status_name}» – результаты приёма не вносятся.</Alert>
      )}
    </>
  );
}

function VisitForm({ a }: { a: Appointment }) {
  const router = useRouter();
  const { user } = useAuth();
  const diagnoses = useLoad(() => api.get<RefItem[]>("/refs/diagnoses"), []);
  const procedures = useLoad(() => api.get<RefItem[]>("/refs/procedures"), []);
  const tests = useLoad(() => api.get<RefItem[]>("/refs/test-types"), []);
  const services = useLoad(() => api.get<RefItem[]>("/refs/services", { specialty: a.doctor.specialty_code }), [a.doctor.specialty_code]);

  const [complaints, setComplaints] = useState("");
  const [icd, setIcd] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [rx, setRx] = useState<RxRow[]>([]);
  const [refs, setRefs] = useState<RefRow[]>([]);
  const [svcState, setSvc] = useState<SvcRow[] | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<Message>(null);
  const [busy, setBusy] = useState(false);

  // основная услуга специальности подставляется по умолчанию, пока врач не изменил список
  const mainService = services.data?.find((s) => s.extra.specialty_code === a.doctor.specialty_code);
  const svc: SvcRow[] = svcState ?? (mainService ? [{ service_code: mainService.code, qty: "1" }] : []);

  const price = (code: string) => Number(services.data?.find((s) => s.code === code)?.extra.price_kzt ?? 0);
  const total = svc.reduce((sum, s) => sum + price(s.service_code) * (Number(s.qty) || 0), 0);

  async function save() {
    const errs: Record<string, string> = {};
    if (!complaints.trim()) errs.complaints = "Укажите жалобы пациента";
    if (!icd) errs.icd_code = "Выберите основной диагноз из справочника МКБ-10";
    rx.forEach((r, i) => {
      const n = Number(r.sessions);
      if (r.procedure_code && !(Number.isInteger(n) && n >= 1 && n <= 30)) errs[`prescriptions.${i}`] = "Количество сеансов – от 1 до 30";
    });
    setErrors(errs);
    if (Object.keys(errs).length) {
      setMsg({ kind: "error", text: "Проверьте заполнение формы приёма" });
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      await api.post(`/doctor/appointments/${a.appt_no}/visit`, {
        complaints,
        icd_code: icd,
        conclusion,
        prescriptions: rx.filter((r) => r.procedure_code).map((r) => ({ ...r, sessions: Number(r.sessions) })),
        referrals: refs.filter((r) => r.test_code),
        services: svc.filter((s) => s.service_code).map((s) => ({ service_code: s.service_code, qty: Number(s.qty) || 1 })),
      });
      router.push(`/doctor?on=${a.date}&saved=1`);
    } catch (e) {
      const err = e as ApiError;
      setErrors(err.fields);
      setMsg({ kind: "error", text: err.message });
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <Card title="Результаты приёма">
        <div className="grid gap-4">
          <Field label="Жалобы" required error={errors.complaints}>
            <Textarea rows={3} value={complaints} onChange={(e) => setComplaints(e.target.value)} invalid={!!errors.complaints} />
          </Field>
          <Field label="Основной диагноз (МКБ-10)" required error={errors.icd_code}>
            <Select value={icd} onChange={(e) => setIcd(e.target.value)} invalid={!!errors.icd_code}>
              <option value="">— выберите из справочника —</option>
              {diagnoses.data?.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.code} — {d.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Заключение и рекомендации">
            <Textarea rows={3} value={conclusion} onChange={(e) => setConclusion(e.target.value)} />
          </Field>
        </div>
      </Card>

      <Card
        title="Назначения процедур"
        actions={<Button size="sm" variant="secondary" onClick={() => setRx([...rx, { procedure_code: "", sessions: "1", instructions: "" }])}>+ Добавить</Button>}
      >
        {rx.length === 0 ? (
          <Empty>Процедуры не назначены</Empty>
        ) : (
          <div className="space-y-3">
            {rx.map((r, i) => (
              <div key={i} className="grid gap-2 sm:grid-cols-[1fr_110px_1fr_auto] sm:items-start">
                <Select value={r.procedure_code} onChange={(e) => setRx(rx.map((x, j) => (j === i ? { ...x, procedure_code: e.target.value } : x)))}>
                  <option value="">— процедура —</option>
                  {procedures.data?.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.name}
                    </option>
                  ))}
                </Select>
                <div>
                  <Input
                    type="number"
                    min={1}
                    max={30}
                    value={r.sessions}
                    aria-label="Сеансов"
                    invalid={!!errors[`prescriptions.${i}`]}
                    onChange={(e) => setRx(rx.map((x, j) => (j === i ? { ...x, sessions: e.target.value } : x)))}
                  />
                  {errors[`prescriptions.${i}`] && <span className="text-xs text-red-700">{errors[`prescriptions.${i}`]}</span>}
                </div>
                <Input placeholder="Указания" value={r.instructions} onChange={(e) => setRx(rx.map((x, j) => (j === i ? { ...x, instructions: e.target.value } : x)))} />
                <Button size="sm" variant="ghost" onClick={() => setRx(rx.filter((_, j) => j !== i))} aria-label="Удалить">
                  ✕
                </Button>
              </div>
            ))}
            <p className="text-xs text-slate-500">Количество сеансов — от 1 до 30. Назначения сразу появятся у медицинской сестры.</p>
          </div>
        )}
      </Card>

      <Card
        title="Направления на исследования"
        actions={<Button size="sm" variant="secondary" onClick={() => setRefs([...refs, { test_code: "", note: "" }])}>+ Добавить</Button>}
      >
        {refs.length === 0 ? (
          <Empty>Направлений нет</Empty>
        ) : (
          <div className="space-y-3">
            {refs.map((r, i) => (
              <div key={i} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <Select value={r.test_code} onChange={(e) => setRefs(refs.map((x, j) => (j === i ? { ...x, test_code: e.target.value } : x)))}>
                  <option value="">— исследование —</option>
                  {tests.data?.map((t) => (
                    <option key={t.code} value={t.code}>
                      {t.name} ({String(t.extra.group)})
                    </option>
                  ))}
                </Select>
                <Input placeholder="Примечание" value={r.note} onChange={(e) => setRefs(refs.map((x, j) => (j === i ? { ...x, note: e.target.value } : x)))} />
                <Button size="sm" variant="ghost" onClick={() => setRefs(refs.filter((_, j) => j !== i))} aria-label="Удалить">
                  ✕
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card
        title="Оказанные услуги"
        actions={<Button size="sm" variant="secondary" onClick={() => setSvc([...svc, { service_code: "", qty: "1" }])}>+ Добавить</Button>}
      >
        {svc.length === 0 ? (
          <Empty>Услуги не указаны</Empty>
        ) : (
          <div className="space-y-3">
            {svc.map((s, i) => (
              <div key={i} className="grid gap-2 sm:grid-cols-[1fr_90px_120px_auto] sm:items-center">
                <Select value={s.service_code} onChange={(e) => setSvc(svc.map((x, j) => (j === i ? { ...x, service_code: e.target.value } : x)))}>
                  <option value="">— услуга —</option>
                  {services.data?.map((x) => (
                    <option key={x.code} value={x.code}>
                      {x.name} · {money(Number(x.extra.price_kzt))}
                    </option>
                  ))}
                </Select>
                <Input type="number" min={1} max={50} value={s.qty} aria-label="Количество" onChange={(e) => setSvc(svc.map((x, j) => (j === i ? { ...x, qty: e.target.value } : x)))} />
                <span className="text-right text-sm tabular-nums">{money(price(s.service_code) * (Number(s.qty) || 0))}</span>
                <Button size="sm" variant="ghost" onClick={() => setSvc(svc.filter((_, j) => j !== i))} aria-label="Удалить">
                  ✕
                </Button>
              </div>
            ))}
            <div className="border-t border-slate-100 pt-2 text-right text-sm font-semibold">Итого: {money(total)}</div>
          </div>
        )}
      </Card>

      <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center gap-3 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur sm:-mx-8 sm:px-8">
        <Button onClick={save} disabled={busy}>
          {busy ? "Сохранение…" : "Сохранить и завершить приём"}
        </Button>
        <LinkButton href={`/doctor?on=${a.date}`}>Отмена</LinkButton>
        <span className="text-xs text-slate-500">Автор: {user?.display_name}</span>
        <Msg m={msg} className="w-full sm:w-auto" />
      </div>
    </div>
  );
}

function VisitResult({ v, onChanged }: { v: Visit; onChanged: (v: Visit) => void }) {
  const diagnoses = useLoad(() => api.get<RefItem[]>("/refs/diagnoses"), []);
  const [edit, setEdit] = useState(false);
  const [complaints, setComplaints] = useState(v.complaints);
  const [icd, setIcd] = useState(v.icd_code);
  const [conclusion, setConclusion] = useState(v.conclusion ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<Message>(null);

  async function save() {
    try {
      const nv = await api.put<Visit>(`/doctor/visits/${v.visit_no}`, { complaints, icd_code: icd, conclusion });
      onChanged(nv);
      setEdit(false);
      setErrors({});
      setMsg({ kind: "ok", text: "Изменения сохранены, прежние значения записаны в историю изменений" });
    } catch (e) {
      setErrors((e as ApiError).fields);
      setMsg({ kind: "error", text: (e as ApiError).message });
    }
  }

  return (
    <div className="space-y-5">
      <Msg m={msg} />
      <Card
        title={`Результаты приёма ${v.visit_no}`}
        actions={!edit && <Button size="sm" variant="secondary" onClick={() => setEdit(true)}>Изменить</Button>}
      >
        {edit ? (
          <div className="grid gap-4">
            <Field label="Жалобы" required error={errors.complaints}>
              <Textarea rows={3} value={complaints} onChange={(e) => setComplaints(e.target.value)} />
            </Field>
            <Field label="Основной диагноз (МКБ-10)" required error={errors.icd_code}>
              <Select value={icd} onChange={(e) => setIcd(e.target.value)}>
                {diagnoses.data?.map((d) => (
                  <option key={d.code} value={d.code}>
                    {d.code} — {d.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Заключение и рекомендации">
              <Textarea rows={3} value={conclusion} onChange={(e) => setConclusion(e.target.value)} />
            </Field>
            <div className="flex gap-2">
              <Button onClick={save}>Сохранить изменения</Button>
              <Button variant="secondary" onClick={() => setEdit(false)}>
                Отмена
              </Button>
            </div>
          </div>
        ) : (
          <Dl
            items={[
              ["Жалобы", v.complaints],
              ["Диагноз", <><Badge className="mr-2 bg-teal-100 font-mono text-teal-900">{v.icd_code}</Badge>{v.diagnosis_name}</>],
              ["Заключение", v.conclusion],
              ["Автор, дата", `${v.author}, ${dmy(v.finished_at)}`],
            ]}
          />
        )}
        {v.changes.length > 0 && (
          <div className="mt-5">
            <h3 className="mb-2 text-sm font-medium text-slate-700">История изменений</h3>
            <Table head={["Когда", "Кто", "Поле", "Было", "Стало"]}>
              {v.changes.map((c, i) => (
                <tr key={i}>
                  <Td className="whitespace-nowrap">{dmy(c.changed_at)}</Td>
                  <Td>{c.changed_by}</Td>
                  <Td>{FIELD_NAMES[c.field] ?? c.field}</Td>
                  <Td>{c.old_value}</Td>
                  <Td>{c.new_value}</Td>
                </tr>
              ))}
            </Table>
          </div>
        )}
      </Card>
      <Card title="Назначения">{v.prescriptions.length ? <RxTable rows={v.prescriptions} /> : <Empty>Нет</Empty>}</Card>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Направления">
          {v.referrals.length ? (
            <ul className="space-y-1 text-sm">
              {v.referrals.map((r) => (
                <li key={r.ref_no}>
                  {r.test_name} · <Badge className={r.status === "DONE" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}>{r.status === "DONE" ? "результат готов" : "ожидает"}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Нет</Empty>
          )}
        </Card>
        <Card title="Оказанные услуги">
          {v.services.length ? (
            <ul className="space-y-1 text-sm">
              {v.services.map((s) => (
                <li key={s.line_no} className="flex justify-between gap-2">
                  <span>{s.service_name}{s.qty > 1 && ` ×${s.qty}`}</span>
                  <span className="tabular-nums">{money(s.amount_kzt)}</span>
                </li>
              ))}
              <li className="flex justify-between border-t border-slate-100 pt-1 font-semibold">
                <span>Итого</span>
                <span className="tabular-nums">{money(v.services_total)}</span>
              </li>
            </ul>
          ) : (
            <Empty>Нет</Empty>
          )}
        </Card>
      </div>
    </div>
  );
}
