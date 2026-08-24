interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: string;
}

export default function StatCard({ label, value, sub, icon }: StatCardProps) {
  return (
    <div className="glass p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        {icon && <span className="text-xl">{icon}</span>}
      </div>
      <p className="mt-2 text-3xl font-bold text-slate-900">
        {value}
        {sub && <span className="ml-1 text-sm font-normal text-gray-400">{sub}</span>}
      </p>
    </div>
  );
}
