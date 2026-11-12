import React from 'react';
import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/forecast', label: 'Forecast' },
  { path: '/accuracy', label: 'Accuracy' },
  { path: '/errors', label: 'Error Heatmap' },
  { path: '/missed-peaks', label: 'Missed Peaks' },
  { path: '/procurement', label: 'Procurement' },
  { path: '/insights', label: 'Insights' },
];

export const Navbar: React.FC = () => {
  return (
    <header className="bg-brand-surface border-b border-brand-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <NavLink to="/forecast" className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-sky-400 flex items-center justify-center font-mono font-bold text-white text-base shadow-lg shadow-cyan-500/20">
                P
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-lg tracking-tight text-brand-text">PeakWise</span>
                <span className="text-[10px] font-mono text-brand-muted tracking-wider uppercase">Delhi DISCOM</span>
              </div>
            </NavLink>

            <nav className="hidden md:flex space-x-1">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-brand-bg text-brand-accent border border-brand-border shadow-inner'
                        : 'text-brand-muted hover:text-brand-text hover:bg-brand-bg/50'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-brand-bg border border-brand-border text-xs font-mono text-brand-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>10:00 IST Origin</span>
            </div>
          </div>
        </div>
      </div>

      <div className="md:hidden flex overflow-x-auto border-t border-brand-border px-4 py-2 space-x-2">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `px-3 py-1 rounded text-xs whitespace-nowrap font-medium ${
                isActive
                  ? 'bg-brand-bg text-brand-accent border border-brand-border'
                  : 'text-brand-muted hover:text-brand-text'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </header>
  );
};
