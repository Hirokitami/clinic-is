import { Suspense } from "react";
import { RoleGate } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import ApptView from "./ApptView";

export const metadata = { title: "Запись на приём" };

export default function Page() {
  return (
    <RoleGate roles={["OPERATOR"]}>
      <Suspense fallback={<Spinner />}>
        <ApptView />
      </Suspense>
    </RoleGate>
  );
}
