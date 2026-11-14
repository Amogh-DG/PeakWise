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
    <div className="bg-[#fef3c7] border-b border-[#fde68a] text-[#92400e] text-sm px-8 py-2.5">
      <div className="max-w-[1440px] mx-auto">
        The API is serving mock data. Numbers below are illustrative.
      </div>
    </div>
  );
};
