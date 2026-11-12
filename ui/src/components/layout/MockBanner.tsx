import React, { useEffect, useState } from 'react';
import { getHealth } from '../../api/client';

export const MockBanner: React.FC = () => {
  const [isMock, setIsMock] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then((res) => {
        if (mounted && res?.mock) {
          setIsMock(true);
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  if (!isMock) return null;

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 text-amber-300 px-4 py-2 text-xs font-mono flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
        <span className="font-semibold tracking-wide uppercase">Mock Mode Active</span>
        <span className="text-amber-400/80 hidden sm:inline">
          — Backend is serving synthetic artifacts (artifacts_mock).
        </span>
      </div>
      <span className="text-[11px] bg-amber-500/20 border border-amber-500/30 px-2 py-0.5 rounded">
        MOCK=1
      </span>
    </div>
  );
};
