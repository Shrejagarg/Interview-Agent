"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Nav() {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  if (loading || !user) return null;

  const isCompany = user.role === "company";

  const candidateLinks = [
    { href: "/interview", label: "Interview" },
    { href: "/history", label: "History" },
  ];

  const companyLinks = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/candidates", label: "Candidates" },
    { href: "/sessions", label: "Sessions" },
    { href: "/compare", label: "Compare" },
    { href: "/invite", label: "Invite" },
    { href: "/campaigns", label: "Campaigns" },
  ];

  const links = isCompany ? companyLinks : candidateLinks;

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200/60 bg-white/80 backdrop-blur-md">
      <div className={`mx-auto flex items-center justify-between px-4 sm:px-6 py-3 ${isCompany ? "max-w-6xl" : "max-w-3xl"}`}>
        <div className="flex items-center gap-1">
          <Link href="/" className="mr-6 text-sm font-bold tracking-tight text-slate-900">
            Interview Agent
          </Link>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                isActive(l.href)
                  ? "bg-slate-900 font-medium text-white"
                  : "text-gray-500 hover:bg-gray-100 hover:text-slate-900"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>
        <div className="text-sm">
          <span className="flex items-center gap-3">
            <span className="text-gray-500">{user.email}</span>
            <span className="rounded-full border border-gray-200 px-2 py-0.5 text-xs text-gray-400">
              {user.role}
            </span>
            <button
              onClick={() => { logout(); router.push("/login"); }}
              className="rounded-lg border border-gray-200 px-3 py-1 text-xs text-gray-500 transition-colors hover:border-gray-300 hover:text-slate-900 cursor-pointer"
            >
              Logout
            </button>
          </span>
        </div>
      </div>
    </nav>
  );
}
