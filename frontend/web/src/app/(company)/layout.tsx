"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function CompanyLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    
    if (!user) {
      router.replace("/login");
    } else if (user.role !== "company") {
      router.replace("/");
    }
  }, [user, loading, router]);

  if (loading || !user || user.role !== "company") {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-slate-900" />
      </div>
    );
  }

  return <>{children}</>;
}
