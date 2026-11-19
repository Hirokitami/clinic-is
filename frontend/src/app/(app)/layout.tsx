import { Suspense } from "react";
import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <AuthProvider>
      <Suspense>
        <AppShell>{children}</AppShell>
      </Suspense>
    </AuthProvider>
  );
}
