import { Suspense } from "react";
import TicketView from "./TicketView";

export const metadata = { title: "Талон на приём" };

export default function Page() {
  return (
    <Suspense>
      <TicketView />
    </Suspense>
  );
}
