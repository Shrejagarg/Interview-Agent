"use client";

import "./globals.css";
import { AuthProvider, useAuth } from "@/lib/auth";
import Link from "next/link";
import { usePathname } from "next/navigation";

function Nav() {
  const { user, logout, loading } = useAuth();
  const path = usePathname();

  if (loading) return null;

  return (
    <nav style={{ padding: "10px 20px", borderBottom: "1px solid #ddd", display: "flex", gap: "16px", alignItems: "center" }}>
      <Link href="/" style={{ fontWeight: "bold", textDecoration: "none", color: "#000" }}>
        Interview Agent
      </Link>
      <Link href="/interview" style={{ textDecoration: "none", color: path === "/interview" ? "#000" : "#666" }}>
        Interview
      </Link>
      <Link href="/history" style={{ textDecoration: "none", color: path === "/history" ? "#000" : "#666" }}>
        History
      </Link>
      <div style={{ marginLeft: "auto" }}>
        {user ? (
          <span>
            {user.email}{" "}
            <button onClick={logout} style={{ cursor: "pointer" }}>[logout]</button>
          </span>
        ) : (
          <span>
            <Link href="/login" style={{ textDecoration: "none" }}>Login</Link>
            {" | "}
            <Link href="/register" style={{ textDecoration: "none" }}>Register</Link>
          </span>
        )}
      </div>
    </nav>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "monospace", margin: 0, padding: 0 }}>
        <AuthProvider>
          <Nav />
          <main style={{ padding: "20px", maxWidth: "900px", margin: "0 auto" }}>
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
