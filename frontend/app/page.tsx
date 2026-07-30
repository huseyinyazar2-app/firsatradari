import type { Metadata } from "next";
import { ResearchDashboard } from "./research-dashboard";

export const metadata: Metadata = {
  title: "Araştırma Masası | Fırsat Radarı",
  description:
    "Kanıttan fırsata izlenebilir, veri temelli araştırma çalışma alanı.",
};

export default function Home() {
  return <ResearchDashboard />;
}
