import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Checkpoint — Git for AI Agent Actions",
  description:
    "Safety, audit, checkpointing and transactional recovery for AI agent actions.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}