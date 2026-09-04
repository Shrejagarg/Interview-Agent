import { useAuth } from "@/lib/auth";
import Link from "next/link";
import ClientMain from "@/components/ClientMain";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-accent selection:text-black">
      {/* 
        HERO SECTION 
        Massive font, grid background from globals.css, borders separating sections
      */}
      <section className="relative w-full border-b border-brutal-border">
        <div className="max-w-[1400px] mx-auto px-4 md:px-8 pt-32 pb-24 flex flex-col items-center">
          
          <h1 className="font-heading text-[12vw] leading-[0.85] text-center tracking-tighter mb-8 max-w-[1200px] mx-auto">
            THE NEW STANDARD <br />
            <span className="text-accent">FOR INTERVIEWS</span>
          </h1>

          <p className="font-sans text-gray-400 max-w-lg text-center text-lg mb-12">
            AI-driven, personalized interview simulations. 
            We build the ultimate training ground for candidates 
            and the ultimate screening tool for companies.
          </p>

          <div className="flex gap-4">
            <Link 
              href="/register" 
              className="bg-accent text-black font-heading text-2xl px-12 py-4 rounded-full transition-transform hover:scale-105"
            >
              START PROJECT ↗
            </Link>
          </div>

          {/* Aesthetic Circular Elements below Hero */}
          <div className="mt-20 flex items-center justify-center gap-4">
            <div className="w-24 h-24 rounded-full bg-brutal-dark border border-brutal-border overflow-hidden">
              <div className="w-full h-full bg-[url('https://images.unsplash.com/photo-1620121692029-d088224ddc74?q=80&w=200&auto=format&fit=crop')] bg-cover opacity-60"></div>
            </div>
            <div className="w-24 h-24 rounded-full bg-brutal-dark border border-brutal-border overflow-hidden">
               <div className="w-full h-full bg-[url('https://images.unsplash.com/photo-1550745165-9bc0b252726f?q=80&w=200&auto=format&fit=crop')] bg-cover opacity-60"></div>
            </div>
            <div className="w-24 h-24 rounded-full bg-accent text-black flex items-center justify-center font-heading text-4xl">
              AI
            </div>
            <div className="w-24 h-24 rounded-full bg-brutal-dark border border-brutal-border overflow-hidden">
               <div className="w-full h-full bg-[url('https://images.unsplash.com/photo-1633477189709-6694176d17fb?q=80&w=200&auto=format&fit=crop')] bg-cover opacity-60"></div>
            </div>
          </div>
        </div>
      </section>

      {/* 
        TICKER SECTION
      */}
      <div className="border-b border-brutal-border py-4 overflow-hidden bg-brutal-dark flex whitespace-nowrap">
        <div className="animate-marquee font-heading text-2xl text-gray-400 tracking-wider flex gap-12 px-6">
          <span>AI EVALUATION</span>
          <span className="text-accent">•</span>
          <span>VOICE INTERVIEWS</span>
          <span className="text-accent">•</span>
          <span>PRE-SCREENING</span>
          <span className="text-accent">•</span>
          <span>ANALYTICS DASHBOARD</span>
          <span className="text-accent">•</span>
          <span>CANDIDATE INSIGHTS</span>
        </div>
      </div>

      {/* 
        FEATURES SECTION - 3 COLUMNS 
      */}
      <section className="border-b border-brutal-border">
        <div className="max-w-[1400px] mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-brutal-border">
            
            <div className="p-12 md:p-16 flex flex-col items-center text-center hover:bg-brutal-dark transition-colors">
              <div className="w-32 h-32 rounded-full border border-brutal-border flex items-center justify-center mb-8">
                <div className="font-heading text-5xl text-accent">01</div>
              </div>
              <h3 className="font-heading text-4xl mb-4 tracking-tight">GENERIC TEMPLATES</h3>
              <p className="font-sans text-gray-500 text-sm leading-relaxed">
                &ldquo;One-size-fits-all&rdquo; never fits. When your interviews feel exactly 
                the same as everyone else&apos;s, candidates lose interest and you miss top talent.
              </p>
            </div>

            <div className="p-12 md:p-16 flex flex-col items-center text-center hover:bg-brutal-dark transition-colors">
              <div className="w-32 h-32 rounded-full border border-brutal-border flex items-center justify-center mb-8">
                <div className="font-heading text-5xl text-accent">02</div>
              </div>
              <h3 className="font-heading text-4xl mb-4 tracking-tight">DYNAMIC VOICE AI</h3>
              <p className="font-sans text-gray-500 text-sm leading-relaxed">
                We generate real-time voice interviews tailored to the candidate&apos;s resume. 
                Our AI digs deep into their experience rather than asking canned questions.
              </p>
              <Link href="/register" className="mt-8 border border-brutal-border rounded-full px-6 py-2 font-heading text-xl hover:bg-white hover:text-black transition-colors">
                CHANGE IT NOW
              </Link>
            </div>

            <div className="p-12 md:p-16 flex flex-col items-center text-center hover:bg-brutal-dark transition-colors">
              <div className="w-32 h-32 rounded-full border border-brutal-border flex items-center justify-center mb-8">
                <div className="font-heading text-5xl text-accent">03</div>
              </div>
              <h3 className="font-heading text-4xl mb-4 tracking-tight">DATA OVERLOAD</h3>
              <p className="font-sans text-gray-500 text-sm leading-relaxed">
                Reading 100 resumes is exhausting. Let our AI conduct the screening interviews 
                and provide you with a ranked dashboard of candidates instantly.
              </p>
            </div>

          </div>
        </div>
      </section>

      {/* 
        HOW WE WORK SECTION
      */}
      <section className="py-24 border-b border-brutal-border">
        <div className="max-w-[1400px] mx-auto px-4 md:px-8 text-center">
          <h2 className="font-heading text-[8vw] leading-none tracking-tighter mb-20">HOW WE WORK</h2>
          
          <div className="flex flex-col md:flex-row justify-between items-start gap-8 max-w-5xl mx-auto text-left">
            {[
              { num: "01", title: "DISCOVER", desc: "Upload resume & select domain." },
              { num: "02", title: "GENERATE", desc: "AI builds custom question graph." },
              { num: "03", title: "CONDUCT", desc: "Real-time voice interview." },
              { num: "04", title: "ANALYZE", desc: "Scoring, transcription, & reporting." }
            ].map((step, i) => (
              <div key={i} className="flex-1 relative w-full border-t border-brutal-border pt-6">
                <div className="font-heading text-6xl text-accent mb-4">{step.num}</div>
                <h4 className="font-heading text-3xl mb-2">{step.title}</h4>
                <p className="font-sans text-sm text-gray-500">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 
        FOOTER
      */}
      <footer className="py-12 text-center text-sm font-sans text-gray-600 bg-brutal-dark">
        <div className="font-heading text-4xl text-gray-500 mb-6">INTERVIEW AGENT</div>
        <p>© 2026 AI Interviewer. Neo-Brutalist Edition.</p>
      </footer>
    </div>
  );
}
