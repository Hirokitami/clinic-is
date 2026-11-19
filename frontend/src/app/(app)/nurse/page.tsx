import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import NurseView from "./NurseView";

export const metadata = { title: "Процедуры" };

export default function Page() {
  return (
    <RoleGate roles={["NURSE"]}>
      <Suspense fallback={<Spinner />}>
        <NurseView />
      </Suspense>
    </RoleGate>
  );
}
