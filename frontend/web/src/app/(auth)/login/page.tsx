"use client";

import { useState, FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push(redirect);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md border border-brutal-border bg-brutal-dark p-10 relative">
        {/* Brutalist accents */}
        <div className="absolute -top-3 -left-3 w-6 h-6 bg-accent rounded-full"></div>
        <div className="absolute -bottom-3 -right-3 w-6 h-6 border-2 border-accent rounded-full"></div>

        <div className="text-center mb-10">
          <h1 className="font-heading text-5xl tracking-wide text-foreground">WELCOME BACK</h1>
          <p className="mt-2 text-sm text-gray-500 font-sans tracking-wide uppercase">SIGN IN TO YOUR ACCOUNT</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-widest font-sans">
              Email Address
            </label>
            <input 
              type="email" 
              placeholder="HELLO@COMPANY.COM" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
              className="w-full border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans uppercase" 
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-widest font-sans">
              Password
            </label>
            <input 
              type="password" 
              placeholder="••••••••" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
              className="w-full border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans" 
            />
          </div>
          
          {error && <div className="border border-red-500/50 bg-red-950/30 p-3 text-sm text-red-400 font-sans">{error}</div>}
          
          <button 
            type="submit" 
            disabled={loading} 
            className="w-full rounded-full bg-accent px-4 py-4 text-xl font-heading text-black transition-transform hover:scale-105 disabled:bg-gray-700 disabled:text-gray-400 cursor-pointer disabled:hover:scale-100 mt-4"
          >
            {loading ? "SIGNING IN..." : "SIGN IN"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-8 font-sans uppercase tracking-widest">
          DON&apos;T HAVE AN ACCOUNT?{" "}
          <Link href="/register" className="text-accent hover:underline">
            REGISTER
          </Link>
        </p>
      </div>
    </div>
  );
}
