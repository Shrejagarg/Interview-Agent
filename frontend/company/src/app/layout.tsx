import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Interview Agent - Company Dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#f8fafc] text-slate-900 antialiased">
        <AuthProvider>
          <Nav />
          <main className="mx-auto max-w-6xl px-4 sm:px-6 py-6">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
