// Add upcoming events here as they're confirmed. Leave empty for the
// empty-state to show automatically.
const UPCOMING_EVENTS = [];

export default function UpcomingEvents() {
  return (
    <section id="upcoming-events" className="relative border-b border-border">
      <div className="max-w-7xl mx-auto px-5 md:px-10 py-14 md:py-24">
        <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 border border-border rounded-full text-xs font-mono tracking-widest text-text-muted uppercase">
          Upcoming Events
        </div>

        <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight leading-tight mb-4 max-w-2xl">
          What's coming up.
        </h2>

        <p className="text-sm md:text-base text-text-muted leading-relaxed max-w-xl mb-10">
          Announcements, hiring drives, and events currently open — check
          back here whenever the notification strip points you this way.
        </p>

        {UPCOMING_EVENTS.length === 0 ? (
          <div className="border border-dashed border-border rounded-xl p-10 md:p-14 text-center">
            <div className="text-sm text-text-muted mb-1">
              No upcoming events right now.
            </div>
            <div className="text-xs text-text-dim">
              Check back soon, or follow us on Instagram for the latest updates.
            </div>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {UPCOMING_EVENTS.map((event) => (
              <div
                key={event.title}
                className="border border-border rounded-lg p-5 bg-surface/60 hover:border-text-dim transition-colors"
              >
                <div className="text-xs font-mono uppercase tracking-widest text-primary-light mb-2">
                  {event.date}
                </div>
                <div className="text-sm font-semibold text-text mb-2">
                  {event.title}
                </div>
                <p className="text-xs md:text-sm text-text-muted leading-relaxed mb-5">
                  {event.description}
                </p>
                <div className="flex items-center gap-4">
                  <button className="px-5 py-2.5 bg-primary hover:bg-primary-light transition-colors rounded-md font-semibold text-sm">
                    Apply Now
                  </button>
                  {event.href && event.href !== '#' && (
                    <a
                      href={event.href}
                      className="inline-flex items-center gap-1.5 text-xs font-mono text-text-muted hover:text-primary-light transition-colors"
                    >
                      See more &rarr;
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}