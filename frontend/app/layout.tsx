import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "RideOps Resolve · Support Operations",
  description:
    "Ticket investigation and operational intelligence for RideOps support teams.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
