"use client";

import { useParams } from "next/navigation";
import { AppointmentManage } from "@/components/AppointmentManage";

export default function MyApptView() {
  const { no } = useParams<{ no: string }>();
  return <AppointmentManage apptNo={no} backHref="/cabinet" backLabel="Мои записи" />;
}
