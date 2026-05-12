import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrashUQ Dashboard",
  description: "Backend-driven federated learning dashboard for Arduino UNO Q",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
