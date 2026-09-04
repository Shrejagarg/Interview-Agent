"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";

export default function ClientMain({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  
  // The landing page handles its own full-width layout
  if (pathname === "/") {
    return <main>{children}</main>;
  }

  // All other functional pages get the standard container
  return (
    <main className="mx-auto max-w-6xl px-4 sm:px-6 py-6 font-sans">
      {children}
    </main>
  );
}
