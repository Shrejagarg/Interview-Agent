"use client";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: string;
}

export default function StatCard({ label, value, sub, icon }: StatCardProps) {
  return (
    <div className="rounded-xl border border-white/20 bg-white/60 backdrop-blur-sm p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">{label}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
          {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
        </div>
        {icon && <span className="text-2xl opacity-60">{icon}</span>}
      </div>
    </div>
  );
}
