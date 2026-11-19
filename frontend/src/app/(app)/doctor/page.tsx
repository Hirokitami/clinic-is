import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import DoctorDayView from "./DoctorDayView";

export const metadata = { title: "Пациенты на приём" };

export default function Page() {
  return (
    <RoleGate roles={["DOCTOR"]}>
      <Suspense fallback={<Spinner />}>
        <DoctorDayView />
      </Suspense>
    </RoleGate>
  );
}
