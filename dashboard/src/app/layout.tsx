import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Employee Dashboard",
  description: "Real-time AI Employee monitoring and management",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
