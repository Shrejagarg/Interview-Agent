"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Nav() {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();

  if (loading) return null;

  const links = [
    { href: "/", label: "Dashboard" },
    { href: "/candidates", label: "Candidates" },
    { href: "/sessions", label: "Sessions" },
    { href: "/compare", label: "Compare" },
    { href: "/invite", label: "Invite" },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200/60 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 sm:px-6 py-3">
        <div className="flex items-center gap-1">
          <Link href="/" className="mr-6 text-sm font-bold tracking-tight text-slate-900">
            Interview Agent
          </Link>
          {user &&
            links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  pathname === l.href
                    ? "bg-slate-900 font-medium text-white"
                    : "text-gray-500 hover:bg-gray-100 hover:text-slate-900"
                }`}
              >
                {l.label}
              </Link>
            ))}
        </div>
        <div className="text-sm">
          {user ? (
            <span className="flex items-center gap-3">
              <span className="text-gray-500">{user.email}</span>
              <button
                onClick={logout}
                className="rounded-lg border border-gray-200 px-3 py-1 text-xs text-gray-500 transition-colors hover:border-gray-300 hover:text-slate-900 cursor-pointer"
              >
                Logout
              </button>
            </span>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-slate-700"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
