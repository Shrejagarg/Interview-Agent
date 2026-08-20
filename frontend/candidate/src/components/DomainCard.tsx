"use client";

import Link from "next/link";

interface DomainCardProps {
  slug: string;
  name: string;
  description: string;
}

export default function DomainCard({ slug, name, description }: DomainCardProps) {
  return (
    <Link
      href={`/interview/${slug}`}
      className="block p-3 border border-gray-200 no-underline text-black hover:border-gray-400 transition-colors"
    >
      <strong>{name}</strong>
      <br />
      <span className="text-sm text-gray-600">{description}</span>
    </Link>
  );
}
