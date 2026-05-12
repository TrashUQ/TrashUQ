import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FederatedCans Dashboard",
  description: "Hardcoded frontend dashboard for federated learning monitoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
