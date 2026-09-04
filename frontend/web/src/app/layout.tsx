import type { Metadata } from "next";
import { Inter, Bebas_Neue } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import Nav from "@/components/Nav";
import ClientMain from "@/components/ClientMain";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const bebasNeue = Bebas_Neue({ weight: "400", subsets: ["latin"], variable: "--font-heading" });

export const metadata: Metadata = {
  title: "Interview Agent",
  description: "AI-powered interview simulator with multi-domain support",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${bebasNeue.variable}`}>
      <body className="min-h-screen bg-[#0A0A0A] text-white antialiased" style={{ fontFamily: "var(--font-heading), sans-serif" }}>
        <AuthProvider>
          <Nav />
          <ClientMain>{children}</ClientMain>
        </AuthProvider>
      </body>
    </html>
  );
}
