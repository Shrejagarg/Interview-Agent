"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Nav() {
  const { user, logout, loading } = useAuth();
  const path = usePathname();

  if (loading) return null;

  const linkStyle = (active: boolean) => ({
    textDecoration: "none",
    color: active ? "#000" : "#666",
    fontWeight: active ? "bold" as const : "normal" as const,
  });

  return (
    <nav className="flex items-center gap-4 px-5 py-2.5 border-b border-gray-200">
      <Link href="/" className="font-bold no-underline text-black">
        Interview Agent
      </Link>
      <Link href="/interview" className="no-underline" style={linkStyle(path === "/interview")}>
        Interview
      </Link>
      <Link href="/history" className="no-underline" style={linkStyle(path === "/history")}>
        History
      </Link>
      <div className="ml-auto">
        {user ? (
          <span className="text-sm">
            {user.email}{" "}
            <button onClick={logout} className="cursor-pointer text-gray-500 hover:text-red-600 text-xs">
              [logout]
            </button>
          </span>
        ) : (
          <span className="text-sm">
            <Link href="/login" className="no-underline text-gray-600 hover:text-black">Login</Link>
            {" | "}
            <Link href="/register" className="no-underline text-gray-600 hover:text-black">Register</Link>
          </span>
        )}
      </div>
    </nav>
  );
}
