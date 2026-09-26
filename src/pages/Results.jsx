import { useParams, Link } from 'react-router-dom';
import { EVENTS } from '../data/events';
import { WORKSHOPS } from '../data/workshops';
import { SEMINARS } from '../data/seminars';

const ALL_ITEMS = [...EVENTS, ...WORKSHOPS, ...SEMINARS];

export default function Results() {
  const { slug } = useParams();
  const item = ALL_ITEMS.find((i) => i.slug === slug);

  return (
    <div className="max-w-3xl mx-auto px-5 md:px-10 py-20 md:py-28 text-center">
      <Link
        to={item ? `/our-work/${item.slug}` : '/our-work'}
        className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-text transition-colors mb-10"
      >
        &larr; Back to {item ? item.title : 'Our Work'}
      </Link>

      <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 border border-border rounded-full text-xs font-mono tracking-widest text-text-muted uppercase">
        Results
      </div>

      <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight leading-tight mb-4">
        {item ? item.title : 'Results'}
      </h1>

      <p className="text-sm md:text-base text-text-muted leading-relaxed">
        Results to be announced. Stay tuned!
      </p>
    </div>
  );
}