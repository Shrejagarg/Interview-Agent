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

export default function DataTable<T extends Record<string, unknown>>({ data, columns, onRowClick, emptyMessage = "NO DATA" }: DataTableProps<T>) {
  if (data.length === 0) {
    return <div className="border border-brutal-border bg-brutal-dark p-12 text-center text-gray-500 uppercase tracking-widest font-bold">{emptyMessage}</div>;
  }
  return (
    <div className="border border-brutal-border bg-brutal-dark overflow-x-auto">
      <table className="w-full text-sm font-sans text-left">
        <thead>
          <tr className="border-b border-brutal-border bg-black text-gray-500 uppercase tracking-widest text-xs">
            {columns.map((c) => (
              <th key={c.key} className={`px-8 py-5 font-bold ${c.align === "right" ? "text-right" : "text-left"}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-brutal-border">
          {data.map((item, i) => (
            <tr key={i} onClick={() => onRowClick?.(item)} className={`transition-colors group ${onRowClick ? "cursor-pointer hover:bg-black" : ""}`}>
              {columns.map((c) => (
                <td key={c.key} className={`px-8 py-5 text-gray-300 font-medium ${onRowClick ? "group-hover:text-foreground" : ""} ${c.align === "right" ? "text-right" : ""}`}>
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
