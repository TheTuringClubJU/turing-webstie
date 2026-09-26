import { Link } from 'react-router-dom';

// Reusable "Results" button — links to the dedicated results page for an
// event. Right now that page just says results are pending; once results
// are finalized, update the Results page's content — this button doesn't
// need to change.
export default function ResultsButton({ slug, className = '', label = 'Results' }) {
  return (
    <Link
      to={`/our-work/${slug}/results`}
      className={`inline-block px-5 py-2.5 border border-border hover:border-text-dim transition-colors rounded-md font-semibold text-sm text-text ${className}`}
    >
      {label}
    </Link>
  );
}