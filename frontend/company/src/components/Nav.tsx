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
    { href: "/sessions", label: "Sessions" },
    { href: "/candidates", label: "Candidates" },
    { href: "/compare", label: "Compare" },
    { href: "/invite", label: "Invite" },
  ];

  return (
    <nav className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200">
      <div className="flex items-center gap-4">
        <Link href="/" className="font-bold text-sm">Interview Agent</Link>
        {user && links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`text-sm ${pathname === l.href ? "font-bold" : "text-gray-500 hover:text-black"}`}
          >
            {l.label}
          </Link>
        ))}
      </div>
      <div className="text-sm">
        {user ? (
          <span>
            {user.email}{" "}
            <button onClick={logout} className="text-gray-500 hover:text-black cursor-pointer">Logout</button>
          </span>
        ) : (
          <Link href="/login" className="text-gray-500 hover:text-black">Login</Link>
        )}
      </div>
    </nav>
  );
}
