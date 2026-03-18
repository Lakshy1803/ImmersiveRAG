import { IngestionManager } from "@/components/Ingestion/IngestionManager";
import { AgentChat } from "@/components/Chat/AgentChat";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12 md:p-12 2xl:p-24 overflow-x-hidden relative">
      {/* Decorative Blur Orbs */}
      <div className="absolute top-0 left-[20%] w-[500px] h-[500px] bg-indigo-600/20 blur-[120px] rounded-full pointer-events-none -translate-y-1/2" />
      <div className="absolute top-1/2 right-[10%] w-[400px] h-[400px] bg-fuchsia-600/20 blur-[120px] rounded-full pointer-events-none -translate-y-1/2" />

      <div className="max-w-[1600px] mx-auto 2xl:my-auto grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-24 relative z-10 items-start mt-8">
        
        {/* Left Column: Config & Upload Dashboard */}
        <section className="flex flex-col h-full animate-in fade-in slide-in-from-left-8 duration-700 ease-out">
           <IngestionManager />
        </section>

        {/* Right Column: Interactive Context Node Search */}
        <section className="flex flex-col h-full items-start lg:items-end animate-in fade-in slide-in-from-right-8 duration-700 ease-out">
           <AgentChat />
        </section>

      </div>
    </main>
  );
}
