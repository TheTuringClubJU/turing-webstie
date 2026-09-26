import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { EVENTS } from '../data/events';
import { WORKSHOPS } from '../data/workshops';
import { SEMINARS } from '../data/seminars';
import ResultsButton from '../components/ResultsButton';

// each category carries its own accent color — used for the tab, the
// card's meta tag, and its border highlight. Add new categories
// (Seminars, Webinars) here with their own color as they go live.
const CATEGORIES = [
  { name: 'Events', color: 'blue' },
  { name: 'Workshops', color: 'teal' },
  { name: 'Seminars', color: 'purple' },
];

const COLOR_STYLES = {
  blue: {
    tabActive: 'bg-primary text-white',
    tag: 'border-blue-500/40 text-blue-300',
    glow: 'rgba(37,99,235,0.14)',
  },
  teal: {
    tabActive: 'bg-teal-500 text-white',
    tag: 'border-teal-500/40 text-teal-300',
    glow: 'rgba(20,184,166,0.14)',
  },
  purple: {
    tabActive: 'bg-purple-500 text-white',
    tag: 'border-purple-500/40 text-purple-300',
    glow: 'rgba(168,85,247,0.14)',
  },
};

const ITEMS = {
  Events: EVENTS,
  Workshops: WORKSHOPS,
  Seminars: SEMINARS,
};

function Card({ item, color }) {
  const styles = COLOR_STYLES[color];
  return (
    <div className="grid sm:grid-cols-2 border border-border rounded-xl overflow-hidden bg-surface/60">
      <div className="p-5 md:p-6 flex flex-col justify-center order-2 sm:order-1">
        <div className="flex items-center gap-2 mb-3">
          <span
            className={`w-fit px-2.5 py-1 border rounded-md text-[11px] font-mono uppercase tracking-wider ${styles.tag}`}
          >
            {item.meta}
          </span>
          {item.date && (
            <span className="text-[11px] text-text-dim font-mono">
              {item.date}
            </span>
          )}
        </div>
        <h3 className="text-lg md:text-xl font-bold text-text mb-2">
          {item.title}
        </h3>
        <p className="text-xs md:text-sm text-text-muted leading-relaxed mb-5">
          {item.description}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            to={`/our-work/${item.slug}`}
            className="w-fit px-4 py-2 border border-border hover:border-text-dim transition-colors rounded-md font-semibold text-xs md:text-sm"
          >
            Read More
          </Link>
          {item.hasResults && (
            <ResultsButton
              slug={item.slug}
              className="!px-4 !py-2 !text-xs md:!text-sm"
            />
          )}
        </div>
      </div>
      <div className="aspect-video sm:aspect-auto bg-surface order-1 sm:order-2">
        <img
          src={item.photos[0]}
          alt={item.title}
          className="w-full h-full object-cover"
        />
      </div>
    </div>
  );
}

export default function OurWork() {
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get('tab');
  const categoryNames = CATEGORIES.map((c) => c.name);
  const [active, setActive] = useState(
    categoryNames.includes(initialTab) ? initialTab : 'Events'
  );
  const items = ITEMS[active] || [];
  const activeCategory = CATEGORIES.find((c) => c.name === active);
  const activeStyles = COLOR_STYLES[activeCategory.color];

  return (
    <div>
      {/* page hero — centered, asymmetric glow behind, tabs near border */}
      <section className="relative border-b border-border overflow-hidden">
        {/* off-center glow: cool blue upper-right, warm amber lower-left —
            asymmetric so it feels like light falling on the page, not a
            centered gradient */}
        <div
          className="absolute inset-0 pointer-events-none transition-[background] duration-500"
          style={{
            background: `radial-gradient(ellipse 500px 400px at 78% 15%, ${activeStyles.glow} 0%, rgba(10,10,10,0) 70%), radial-gradient(ellipse 400px 350px at 12% 90%, rgba(245,158,11,0.06) 0%, rgba(10,10,10,0) 70%)`,
          }}
        />

        <div className="relative max-w-7xl mx-auto px-5 md:px-10 pt-14 pb-8 md:pt-20 md:pb-10 text-center">
          <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 border border-border rounded-full text-xs font-mono tracking-widest text-text-muted uppercase">
            Our Work
          </div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-tight mb-4 max-w-2xl mx-auto">
            Everything we've run and built.
          </h1>
          <p className="text-sm md:text-base text-text-muted leading-relaxed max-w-xl mx-auto mb-10">
            Hackathons, workshops, seminars, and webinars — a running record
            of what the Turing Club has organized and shipped.
          </p>

          {/* tabs — color-coded per category, bigger, close to the border below */}
          <div className="flex flex-wrap justify-center gap-3">
            {CATEGORIES.map((cat) => {
              const styles = COLOR_STYLES[cat.color];
              const isActive = active === cat.name;
              return (
                <button
                  key={cat.name}
                  onClick={() => setActive(cat.name)}
                  className={`px-6 py-3 rounded-md text-sm md:text-base font-semibold transition-colors ${
                    isActive
                      ? styles.tabActive
                      : 'border border-border text-text-muted hover:border-text-dim'
                  }`}
                >
                  {cat.name}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* cards */}
      <section className="relative border-b border-border">
        <div className="max-w-7xl mx-auto px-5 md:px-10 py-12 md:py-16">
          {items.length === 0 ? (
            <div className="border border-dashed border-border rounded-xl p-10 md:p-14 text-center">
              <div className="text-sm text-text-muted mb-1">
                Nothing here yet.
              </div>
              <div className="text-xs text-text-dim">
                Check back soon — {active.toLowerCase()} will show up here
                once they're confirmed.
              </div>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-5">
              {items.map((item) => (
                <Card key={item.slug} item={item} color={activeCategory.color} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}