import type { ProjectVisual } from "@/content/site";

const chip = "rounded-[20px] bg-[#eef0ff] px-2 py-1 font-mono text-[11px] text-[#3442ff]";

function Rag() {
  return (
    <div className="flex w-[84%] flex-col gap-2 sm:w-[62%] sm:gap-2.5">
      <div className="self-end rounded-[14px] rounded-br-[4px] bg-ink px-3 py-2.5 text-xs sm:px-3.5 sm:py-3 sm:text-[13px] leading-[1.4] text-white shadow-[0_10px_30px_rgba(0,0,0,.06)]">
        Which clauses changed between v2 and v3 of the policy?
      </div>
      <div className="rounded-[14px] rounded-bl-[4px] bg-white px-3 py-2.5 text-xs sm:px-3.5 sm:py-3 sm:text-[13px] leading-[1.4] shadow-[0_10px_30px_rgba(0,0,0,.06)]">
        Three clauses changed. The biggest: claim window went from 30 to 45 days.
        <div className="mt-2 flex flex-wrap gap-1.5">
          <span className={chip}>plan</span>
          <span className={chip}>retrieve ×4</span>
          <span className={chip}>compare</span>
          <span className="rounded-[20px] bg-[#e5f8ec] px-2 py-1 font-mono text-[11px] text-[#11934a]">✓ verified</span>
        </div>
      </div>
    </div>
  );
}

function Stake() {
  return (
    <div className="w-[64%] rounded-[18px] bg-[linear-gradient(160deg,#6d2bff,#2b3bff_60%,#00c2ff)] p-4 text-white shadow-[0_30px_60px_rgba(60,40,255,.35)] sm:w-[52%] sm:p-5">
      <div className="font-mono text-[11px] opacity-75">YOUR STAKE</div>
      <div className="mb-2.5 mt-1 whitespace-nowrap text-[30px] font-medium sm:mb-3.5 sm:text-[40px] tracking-[-0.04em]">32.40 ETH</div>
      <div className="flex justify-between border-t border-white/20 py-2 text-[13px]">
        <span>Receive</span>
        <span>32.18 stETH</span>
      </div>
      <div className="flex justify-between border-t border-white/20 py-2 text-[13px]">
        <span>Rewards</span>
        <span>3.9% APR</span>
      </div>
      <div className="mt-3 rounded-[10px] bg-white p-[9px] text-center text-[13px] font-medium text-[#2b3bff]">Stake</div>
    </div>
  );
}

function Cert() {
  return (
    <div className="relative w-[72%] -rotate-3 rounded-lg bg-white p-4 sm:w-[56%] sm:p-[22px] shadow-[0_20px_50px_rgba(0,0,0,.08)]">
      <div className="text-[11px] uppercase tracking-[.2em] text-soft">Certificate of completion</div>
      <div className="mb-1 mt-2.5 text-lg sm:text-[22px] font-medium tracking-[-0.03em]">Aarav Mehta</div>
      <div className="mt-2 h-1.5 w-[80%] rounded-[3px] bg-card" />
      <div className="mt-2 h-1.5 w-[60%] rounded-[3px] bg-card" />
      <div className="mt-4 font-mono text-[10px] text-[#11934a]">0x7f3a…e91c · anchored on-chain</div>
      <div className="absolute -bottom-3 -right-3 grid h-16 w-16 sm:-bottom-[18px] sm:-right-[18px] sm:h-[82px] sm:w-[82px] rotate-12 place-items-center rounded-full bg-[#ffcf24] text-center font-mono text-[10px] font-semibold sm:text-[11px] leading-[1.2] shadow-[0_10px_25px_rgba(255,180,0,.45)]">
        <span>
          VERI
          <br />
          FIED
        </span>
      </div>
    </div>
  );
}

export function WorkVisual({ kind }: { kind: ProjectVisual }) {
  if (kind === "rag") return <Rag />;
  if (kind === "stake") return <Stake />;
  return <Cert />;
}
