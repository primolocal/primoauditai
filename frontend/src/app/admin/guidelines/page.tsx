'use client';
import dynamic from 'next/dynamic';

const GuidelinesAdminPage = dynamic(() => import('./content'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen bg-slate-50 p-12 flex items-center justify-center">
      <div className="text-slate-400 font-medium animate-pulse">Loading Guidelines Manager...</div>
    </div>
  ),
});

export default function GuidelinesPage() {
  return <GuidelinesAdminPage />;
}
