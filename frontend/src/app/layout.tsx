import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "ИС медицинской клиники", template: "%s · ИС клиники" },
  description: "Регистратура, расписание врачей, приём пациента, процедуры, личный кабинет",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
