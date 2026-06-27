import { redirect } from "next/navigation";
import { ROUTES } from "@/constants";

export default function PortalPage() {
  redirect(ROUTES.DASHBOARD);
}
