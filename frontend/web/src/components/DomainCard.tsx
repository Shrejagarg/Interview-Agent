export default function DomainCard({ name, description }: { slug: string; name: string; description: string }) {
  return (
    <div className="glass p-4">
      <p className="text-sm font-bold text-slate-900">{name}</p>
      <p className="mt-1 text-xs text-gray-500">{description}</p>
    </div>
  );
}
