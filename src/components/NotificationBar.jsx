import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { notification } from '../data/notification';

const MINIMIZED_KEY_PREFIX = 'ttc-notification-minimized:';

export default function NotificationBar() {
  const [status, setStatus] = useState('hidden'); // 'hidden' | 'expanded' | 'minimized'

  useEffect(() => {
    if (!notification.active) return;

    const isExpired = new Date() > new Date(notification.expiresAt);
    if (isExpired) return;

    const isMinimized = localStorage.getItem(
      `${MINIMIZED_KEY_PREFIX}${notification.id}`
    );
    setStatus(isMinimized ? 'minimized' : 'expanded');
  }, []);

  const minimize = () => {
    localStorage.setItem(`${MINIMIZED_KEY_PREFIX}${notification.id}`, '1');
    setStatus('minimized');
  };

  const expand = () => {
    localStorage.removeItem(`${MINIMIZED_KEY_PREFIX}${notification.id}`);
    setStatus('expanded');
  };

  if (status === 'hidden') return null;

  // minimized: small pill, doesn't take up the full strip
  if (status === 'minimized') {
    return (
      <div className="sticky top-20 z-40 flex justify-end px-5 md:px-10 py-1.5 border-b border-border bg-bg">
        <button
          onClick={expand}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-200 text-[11px] font-mono hover:bg-amber-500/20 transition-colors"
        >
          <span className="relative flex h-1.5 w-1.5 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-400" />
          </span>
          Announcement
        </button>
      </div>
    );
  }

  // expanded: full strip
  return (
    <div className="sticky top-20 z-40 border-b border-amber-500/30 bg-amber-500/10 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-5 md:px-10 py-2.5 flex items-center gap-3">
        <span className="relative flex h-2 w-2 shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
        </span>

        <Link
          to={notification.href}
          className="flex-1 min-w-0 text-xs sm:text-sm font-medium text-amber-200 hover:text-amber-100 transition-colors truncate"
        >
          {notification.message}
          {notification.date && (
            <span className="hidden sm:inline ml-2 text-[11px] font-mono text-amber-300/70">
              &middot; {notification.date}
            </span>
          )}
        </Link>

        <Link
          to={notification.href}
          className="hidden sm:inline text-xs font-mono text-amber-300/80 hover:text-amber-100 transition-colors whitespace-nowrap"
        >
          View Results &rarr;
        </Link>

        <button
          onClick={minimize}
          aria-label="Minimize notification"
          title="Minimize"
          className="shrink-0 p-1 text-amber-300/70 hover:text-amber-100 transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <path d="M5 12h14" />
          </svg>
        </button>
      </div>
    </div>
  );
}