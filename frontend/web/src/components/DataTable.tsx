"use client";

import { ReactNode } from "react";

interface Column<T> {
  key: string;
  label: string;
  align?: "left" | "right";
  render?: (item: T) => ReactNode;
}

interface DataTableProps<T extends Record<string, unknown>> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
}

export default function DataTable<T extends Record<string, unknown>>({ data, columns, onRowClick, emptyMessage = "No data" }: DataTableProps<T>) {
  if (data.length === 0) {
    return <div className="glass p-12 text-center text-gray-400">{emptyMessage}</div>;
  }
  return (
    <div className="glass overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50/50">
            {columns.map((c) => (
              <th key={c.key} className={`px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500 ${c.align === "right" ? "text-right" : "text-left"}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.map((item, i) => (
            <tr key={i} onClick={() => onRowClick?.(item)} className={`transition-colors ${onRowClick ? "cursor-pointer hover:bg-gray-50/80" : ""}`}>
              {columns.map((c) => (
                <td key={c.key} className={`px-4 py-3 ${c.align === "right" ? "text-right" : ""}`}>
                  {c.render ? c.render(item) : String(item[c.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
