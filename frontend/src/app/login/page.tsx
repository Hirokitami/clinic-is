import { Suspense } from "react";
import LoginForm from "./LoginForm";

export const metadata = { title: "Вход" };

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-teal-50 via-slate-50 to-sky-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-teal-700 text-2xl text-white">
            +
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-slate-900">ИС медицинской клиники</h1>
          <p className="text-sm text-slate-600">Вход в систему</p>
        </div>
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
