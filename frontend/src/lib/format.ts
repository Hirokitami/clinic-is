const MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
  "ноября", "декабря"];
export const WEEKDAYS_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];
export const WEEKDAYS_FULL = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];

function parse(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** Индекс дня недели: 0 – понедельник. */
export function weekdayIndex(iso: string): number {
  return (parse(iso).getDay() + 6) % 7;
}

export function ruDate(iso: string | null | undefined, weekday = false): string {
  if (!iso) return "";
  const d = parse(iso);
  const text = `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  return weekday ? `${text} (${WEEKDAYS_SHORT[weekdayIndex(iso)]})` : text;
}

export function dmy(iso: string | null | undefined): string {
  if (!iso) return "";
  const [y, m, d] = iso.slice(0, 10).split("-");
  const time = iso.length > 10 ? " " + iso.slice(11, 16) : "";
  return `${d}.${m}.${y}${time}`;
}

export function todayIso(): string {
  const d = new Date();
  return toIso(d);
}

export function toIso(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function addDays(iso: string, days: number): string {
  const d = parse(iso);
  d.setDate(d.getDate() + days);
  return toIso(d);
}

export function money(v: number): string {
  return new Intl.NumberFormat("ru-RU").format(v) + " ₸";
}

export function age(birthIso: string): number {
  const b = parse(birthIso);
  const n = new Date();
  let a = n.getFullYear() - b.getFullYear();
  if (n.getMonth() < b.getMonth() || (n.getMonth() === b.getMonth() && n.getDate() < b.getDate())) a--;
  return a;
}

export const FIELD_NAMES: Record<string, string> = {
  complaints: "Жалобы",
  icd_code: "Диагноз",
  conclusion: "Заключение",
};
