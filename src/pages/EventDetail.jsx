import { useParams, Link } from 'react-router-dom';
import { EVENTS } from '../data/events';
import { WORKSHOPS } from '../data/workshops';
import { SEMINARS } from '../data/seminars';
import ResultsButton from '../components/ResultsButton';

const ALL_ITEMS = [...EVENTS, ...WORKSHOPS, ...SEMINARS];

const CATEGORY_COLOR = {
  Events: 'border-blue-500/40 text-blue-300',
  Workshops: 'border-teal-500/40 text-teal-300',
  Seminars: 'border-purple-500/40 text-purple-300',
};

export default function EventDetail() {
  const { slug } = useParams();
  const item = ALL_ITEMS.find((i) => i.slug === slug);

  if (!item) {
    return (
      <div className="max-w-7xl mx-auto px-5 md:px-10 py-20 text-center">
        <h1 className="text-2xl font-bold mb-4">Not found.</h1>
        <p className="text-sm text-text-muted mb-8">
          This event doesn't exist or may have been moved.
        </p>
        <Link
          to="/our-work"
          className="px-5 py-2.5 border border-border hover:border-text-dim transition-colors rounded-md font-semibold text-sm"
        >
          Back to Our Work
        </Link>
      </div>
    );
  }

  const tagStyle = CATEGORY_COLOR[item.category] || CATEGORY_COLOR.Events;

  return (
    <div>
      <section className="relative border-b border-border">
        <div className="max-w-5xl mx-auto px-5 md:px-10 pt-10 pb-12 md:pt-14 md:pb-16">
          <Link
            to={`/our-work?tab=${item.category}`}
            className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-text transition-colors mb-8"
          >
            &larr; Back to {item.category}
          </Link>

          <div className="flex items-center gap-3 mb-5">
            <span
              className={`px-2.5 py-1 border rounded-md text-[11px] font-mono uppercase tracking-wider ${tagStyle}`}
            >
              {item.meta}
            </span>
            {item.date && (
              <span className="text-xs text-text-dim font-mono">
                {item.date}
              </span>
            )}
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-tight mb-6">
            {item.title}
          </h1>

          <p className="text-sm md:text-base text-text-muted leading-relaxed max-w-3xl">
            {item.description}
          </p>

          {item.hasResults && <ResultsButton slug={item.slug} className="mt-6" />}
        </div>
      </section>

      <section className="relative">
        <div className="max-w-5xl mx-auto px-5 md:px-10 py-12 md:py-16">
          <div
            className={`grid gap-3 ${
              item.photos.length > 1 ? 'sm:grid-cols-2' : ''
            }`}
          >
            {item.photos.map((src, i) => (
              <div
                key={i}
                className="aspect-video rounded-lg overflow-hidden border border-border bg-surface"
              >
                <img
                  src={src}
                  alt={`${item.title} photo ${i + 1}`}
                  className="w-full h-full object-cover"
                />
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}