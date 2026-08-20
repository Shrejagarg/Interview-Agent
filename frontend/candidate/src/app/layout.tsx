import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import Nav from "@/components/Nav";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  display: "swap",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Interview Agent",
  description: "AI-powered interview simulator — practice across 5 domains with instant LLM evaluation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans m-0 p-0`}>
        <AuthProvider>
          <Nav />
          <main className="p-5 max-w-[900px] mx-auto">
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
