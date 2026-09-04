interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: string;
}

export default function StatCard({ label, value, sub, icon }: StatCardProps) {
  return (
    <div className="border border-brutal-border bg-brutal-dark p-6 transition-colors hover:bg-black group">
      <div className="flex items-center justify-between border-b border-brutal-border pb-4 mb-4">
        <p className="text-sm font-bold uppercase tracking-widest text-gray-500 font-sans group-hover:text-accent transition-colors">{label}</p>
        {icon && <span className="text-2xl grayscale group-hover:grayscale-0 transition-all">{icon}</span>}
      </div>
      <p className="font-heading text-6xl text-foreground">
        {value}
        {sub && <span className="ml-2 text-xl font-heading text-gray-500">{sub}</span>}
      </p>
    </div>
  );
}
