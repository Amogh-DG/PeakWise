import React from 'react';
import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/forecast', label: 'Forecast' },
  { path: '/accuracy', label: 'Accuracy' },
  { path: '/errors', label: 'Error heatmap' },
  { path: '/missed-peaks', label: 'Missed peaks' },
  { path: '/procurement', label: 'Procurement' },
  { path: '/insights', label: 'Insights' },
];

export const Navbar: React.FC = () => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-[1440px] mx-auto px-8">
        <div className="flex items-center h-16">
          <NavLink to="/forecast" className="text-lg font-bold text-slate-900 tracking-tight mr-10">
            Peak Load Forecast
          </NavLink>

          <nav className="flex items-center space-x-2">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `px-4 py-1.5 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-[#e0edfd] text-[#1e40af] font-medium'
                      : 'text-slate-600 hover:text-slate-900 font-normal'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
};
