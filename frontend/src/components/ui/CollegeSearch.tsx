import React, { useState, useEffect, useRef } from 'react';
import { collegesApi, College } from '../../lib/api';

interface CollegeSearchProps {
  value: College | null;
  onChange: (college: College | null) => void;
  error?: string;
  disabled?: boolean;
}

export default function CollegeSearch({ value, onChange, error, disabled }: CollegeSearchProps) {
  const [query, setQuery] = useState(value?.college_name ?? '');
  const [results, setResults] = useState<College[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [focused, setFocused] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [highlightedIdx, setHighlightedIdx] = useState(-1);

  useEffect(() => {
    if (value) setQuery(value.college_name);
  }, [value]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        if (!value) setQuery('');
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [value]);

  const search = (q: string) => {
    setQuery(q);
    if (value) onChange(null); // Clear selection when typing again

    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q.trim() || q.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await collegesApi.search(q);
        setResults(res.data);
        setIsOpen(true);
        setHighlightedIdx(-1);
      } catch {
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);
  };

  const select = (college: College) => {
    onChange(college);
    setQuery(college.college_name);
    setIsOpen(false);
    setResults([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || results.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIdx(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIdx(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIdx >= 0 && results[highlightedIdx]) {
        select(results[highlightedIdx]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className="college-search" ref={containerRef}>
      <div className={`college-search__input-wrap ${focused ? 'focused' : ''} ${error ? 'error' : ''} ${value ? 'has-value' : ''}`}>
        <svg className="college-search__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 10v6M2 10l10-5 10 5-10 5z" /><path d="M6 12v5c3 3 9 3 12 0v-5" />
        </svg>
        <input
          type="text"
          className="college-search__input"
          placeholder="Search your college or university..."
          value={query}
          onChange={e => search(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => { setFocused(true); if (results.length > 0) setIsOpen(true); }}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          autoComplete="off"
        />
        {isLoading && <div className="college-search__spinner" />}
        {value && (
          <button className="college-search__clear" onClick={() => { onChange(null); setQuery(''); setResults([]); }}>
            ✕
          </button>
        )}
      </div>

      {value && (
        <div className="college-search__selected-badge">
          <span className="badge-dot" />
          Selected: {value.college_name} — {value.state}
        </div>
      )}

      {isOpen && results.length > 0 && (
        <ul className="college-search__dropdown" ref={listRef} role="listbox">
          {results.map((college, idx) => (
            <li
              key={college.id}
              className={`college-search__item ${idx === highlightedIdx ? 'highlighted' : ''}`}
              role="option"
              aria-selected={idx === highlightedIdx}
              onMouseDown={() => select(college)}
              onMouseEnter={() => setHighlightedIdx(idx)}
            >
              <div className="college-search__item-name">{college.college_name}</div>
              <div className="college-search__item-meta">
                {college.university && <span>{college.university} · </span>}
                <span>{college.district ? `${college.district}, ` : ''}{college.state}</span>
              </div>
            </li>
          ))}
        </ul>
      )}

      {isOpen && !isLoading && results.length === 0 && query.length >= 2 && (
        <div className="college-search__empty">
          <p>No results for "<strong>{query}</strong>"</p>
          <p className="college-search__empty-hint">Can't find your college? Try searching by city, state, or a shorter name.</p>
        </div>
      )}

      {error && <p className="college-search__error">{error}</p>}
    </div>
  );
}
