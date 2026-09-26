import NeuralNetDiagram from './NeuralNetDiagram';
import TerminalPanel from './TerminalPanel';
import ResultsButton from './ResultsButton';

export default function Hero() {
  return (
    <section id="home" className="relative border-b border-border overflow-hidden">
      {/* full-bleed faint diagram backdrop, ties the whole hero together */}
      <NeuralNetDiagram className="absolute inset-0 w-full h-full opacity-70" />

      {/* soft glow tying into the diagram/terminal area */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 900px 500px at 68% 55%, rgba(37,99,235,0.10) 0%, rgba(10,10,10,0) 70%)',
        }}
      />

      {/* fade backdrop toward the left so text stays crisp */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'linear-gradient(to right, #0a0a0a 0%, #0a0a0a 35%, rgba(10,10,10,0.4) 60%, rgba(10,10,10,0.1) 100%)',
        }}
      />

      <div className="relative max-w-7xl mx-auto px-5 md:px-10 pt-12 pb-10 md:pt-20 md:pb-14">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 mb-5 px-3 py-1.5 border border-border rounded-full text-[10px] sm:text-xs font-mono tracking-widest text-text-muted uppercase">
            Events &middot; Hackathons &middot; Workshops
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold leading-[1.12] tracking-tight mb-4">
            We Run the Events.
            <br />
            <span className="text-primary-light">You Do the Building.</span>
          </h1>

          <p className="max-w-xl text-sm md:text-base text-text-muted leading-relaxed mb-6">
            From AI/ML challenges to full-stack hackathons, the Turing Club
            creates the platform for students to build real projects and
            compete for real stakes.
          </p>

          {/* domain tags */}
          <div className="flex flex-wrap gap-2 mb-6">
            {['AI/ML', 'Web Dev', 'Cybersecurity', 'Data Science'].map((tag) => (
              <span
                key={tag}
                className="px-2.5 py-1 border border-border rounded-md text-[11px] sm:text-xs text-text-muted font-mono"
              >
                {tag}
              </span>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-start gap-3 mb-6">
            <button className="w-full sm:w-auto px-6 py-3 bg-primary hover:bg-primary-light transition-colors rounded-md font-semibold text-sm">
              Apply to Join
            </button>
            <a
              href="#upcoming-events"
              className="w-full sm:w-auto px-6 py-3 border border-border hover:border-text-dim transition-colors rounded-md font-semibold text-sm text-center"
            >
              See Upcoming Events
            </a>
          </div>

          {/* hiring results card */}
          <div className="max-w-md px-3.5 sm:px-4 py-3 border border-border rounded-lg bg-surface/60">
            <div className="flex items-center gap-3 sm:gap-4">
              <span className="relative flex h-2 w-2 shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-light opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-light" />
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] sm:text-[11px] font-mono uppercase tracking-widest text-text-dim">
                  Hiring &middot; 2nd &amp; 3rd Year Students
                </div>
                <div className="text-xs sm:text-sm text-text font-medium truncate">
                  Applications closed &mdash; results pending
                </div>
              </div>
            </div>
            <ResultsButton slug="hiring-2nd-3rd-year-2026" className="mt-3" />
          </div>
        </div>

        {/* terminal: single foreground element, overlapping into the diagram backdrop */}
        <TerminalPanel className="hidden lg:block absolute right-10 md:right-16 lg:right-24 top-1/2 -translate-y-1/2 w-[300px]" />

        {/* mobile: terminal stacked below copy */}
        <TerminalPanel className="lg:hidden mt-8 w-full max-w-xs mx-auto" />
      </div>
    </section>
  );
}