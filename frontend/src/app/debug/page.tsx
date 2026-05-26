'use client';
import dynamic from 'next/dynamic';

const DebugPage = dynamic(() => import('./content'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#0B0F14' }}>
      <div className="text-cyan-400 font-bold animate-pulse">Loading Debug Console...</div>
    </div>
  ),
});

export default function DebugPageWrapper() {
  return <DebugPage />;
}
