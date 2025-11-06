import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent4BA - AI-Powered Backlog Management",
  description: "Real-time backlog management with AI assistance",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
