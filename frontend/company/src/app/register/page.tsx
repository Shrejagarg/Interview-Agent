"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await register(email, password, fullName);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto mt-20">
      <h1 className="text-xl font-bold mb-4">Company Registration</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full Name" className="p-2 border border-gray-200" />
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" required className="p-2 border border-gray-200" />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" required minLength={8} className="p-2 border border-gray-200" />
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button type="submit" disabled={loading} className="px-4 py-2 bg-black text-white hover:bg-gray-800 disabled:bg-gray-300 cursor-pointer">
          {loading ? "Registering..." : "Register"}
        </button>
      </form>
      <p className="text-sm text-gray-500 mt-3">
        Already have an account? <Link href="/login" className="text-blue-600 hover:underline">Login</Link>
      </p>
    </div>
  );
}
