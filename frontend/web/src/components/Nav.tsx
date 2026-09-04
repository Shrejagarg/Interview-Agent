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
    { href: "/interview", label: "INTERVIEW" },
    { href: "/history", label: "HISTORY" },
  ];

  const companyLinks = [
    { href: "/dashboard", label: "DASHBOARD" },
    { href: "/candidates", label: "CANDIDATES" },
    { href: "/sessions", label: "SESSIONS" },
    { href: "/compare", label: "COMPARE" },
    { href: "/invite", label: "INVITE" },
    { href: "/campaigns", label: "CAMPAIGNS" },
  ];

  const links = isCompany ? companyLinks : candidateLinks;

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");

  return (
    <nav className="sticky top-0 z-50 border-b border-brutal-border bg-background">
      <div className={`mx-auto flex h-16 items-center justify-between px-4 sm:px-6 w-full max-w-7xl`}>
        <div className="flex items-center gap-8">
          <Link href="/" className="font-heading text-2xl tracking-wide text-foreground">
            INTERVIEW AGENT
          </Link>
          <div className="hidden md:flex items-center gap-1">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`font-heading text-lg tracking-wide px-4 py-2 transition-colors ${
                  isActive(l.href)
                    ? "text-accent border-b-2 border-accent"
                    : "text-gray-400 hover:text-foreground"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm font-sans">
          <div className="hidden md:flex items-center gap-3">
            <span className="text-gray-400">{user.email}</span>
            <span className="border border-brutal-border bg-brutal-dark px-2 py-0.5 text-xs uppercase tracking-widest text-gray-300">
              {user.role}
            </span>
          </div>
          <button
            onClick={() => { logout(); router.push("/login"); }}
            className="border border-brutal-border px-4 py-1.5 text-xs uppercase tracking-wider text-gray-400 transition-colors hover:border-accent hover:text-accent cursor-pointer"
          >
            LOGOUT
          </button>
        </div>
      </div>
    </nav>
  );
}
