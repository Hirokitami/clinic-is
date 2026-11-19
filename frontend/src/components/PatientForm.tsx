"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Button, Field, Input, Select } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Patient } from "@/lib/types";

type Data = Record<
  "iin" | "last_name" | "first_name" | "middle_name" | "birth_date" | "sex" | "mobile_phone" | "address" | "doc_type" | "doc_no",
  string
>;

const EMPTY: Data = {
  iin: "",
  last_name: "",
  first_name: "",
  middle_name: "",
  birth_date: "",
  sex: "",
  mobile_phone: "",
  address: "",
  doc_type: "",
  doc_no: "",
};

function fromPatient(p: Patient): Data {
  const d = { ...EMPTY };
  for (const k of Object.keys(d) as (keyof Data)[]) d[k] = (p[k as keyof Patient] as string | null) ?? "";
  return d;
}

/** Ввод и изменение данных электронной карты (Т2, Т3). Обязательные поля отмечены *. */
export function PatientForm({
  patient,
  initialIin,
  onSaved,
}: {
  patient?: Patient;
  initialIin?: string;
  onSaved: (p: Patient) => void;
}) {
  const isNew = !patient;
  const [d, setD] = useState<Data>(patient ? fromPatient(patient) : { ...EMPTY, iin: initialIin ?? "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState("");
  const [existing, setExisting] = useState<Patient | null>(null);
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k: keyof Data) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setD((x) => ({ ...x, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setGeneral("");
    setExisting(null);
    setOk("");
    try {
      const p = isNew ? await api.post<Patient>("/patients", d) : await api.put<Patient>(`/patients/${patient.iin}`, d);
      if (!isNew) setOk("Изменения сохранены");
      onSaved(p);
    } catch (err) {
      const e2 = err as ApiError;
      setErrors(e2.fields);
      setGeneral(e2.message);
      if (e2.detail.existing) setExisting(e2.detail.existing as unknown as Patient);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      {general && (
        <Alert kind="error">
          {general}
          {existing && (
            <>
              {" "}
              — <Link className="font-medium underline" href={`/registry/patients/${existing.iin}`}>открыть карту {existing.fio}</Link>
            </>
          )}
        </Alert>
      )}
      {ok && <Alert kind="ok">{ok}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="ИИН" required error={errors.iin} hint={isNew ? "12 цифр" : "ИИН не изменяется"}>
          <Input
            value={d.iin}
            disabled={!isNew}
            inputMode="numeric"
            maxLength={12}
            invalid={!!errors.iin}
            onChange={(e) => setD((x) => ({ ...x, iin: e.target.value.replace(/\D/g, "") }))}
          />
        </Field>
        <Field label="Фамилия" required error={errors.last_name}>
          <Input value={d.last_name} onChange={set("last_name")} invalid={!!errors.last_name} />
        </Field>
        <Field label="Имя" required error={errors.first_name}>
          <Input value={d.first_name} onChange={set("first_name")} invalid={!!errors.first_name} />
        </Field>
        <Field label="Отчество">
          <Input value={d.middle_name} onChange={set("middle_name")} />
        </Field>
        <Field label="Дата рождения" required error={errors.birth_date}>
          <Input type="date" value={d.birth_date} onChange={set("birth_date")} invalid={!!errors.birth_date} />
        </Field>
        <Field label="Пол" error={errors.sex}>
          <Select value={d.sex} onChange={set("sex")}>
            <option value="">—</option>
            <option value="М">Мужской</option>
            <option value="Ж">Женский</option>
          </Select>
        </Field>
        <Field label="Мобильный телефон" required error={errors.mobile_phone} hint="Для SMS-подтверждений">
          <Input value={d.mobile_phone} onChange={set("mobile_phone")} placeholder="+7 701 234 56 78" invalid={!!errors.mobile_phone} />
        </Field>
        <Field label="Адрес" className="sm:col-span-2">
          <Input value={d.address} onChange={set("address")} />
        </Field>
        <Field label="Вид документа">
          <Select value={d.doc_type} onChange={set("doc_type")}>
            <option value="">—</option>
            <option>Удостоверение личности</option>
            <option>Паспорт РК</option>
            <option>Свидетельство о рождении</option>
            <option>Вид на жительство</option>
          </Select>
        </Field>
        <Field label="Номер документа">
          <Input value={d.doc_no} onChange={set("doc_no")} />
        </Field>
      </div>
      <Button type="submit" disabled={busy}>
        {isNew ? "Зарегистрировать" : "Сохранить изменения"}
      </Button>
    </form>
  );
}
