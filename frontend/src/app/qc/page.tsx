'use client';
import dynamic from 'next/dynamic';

const QCPage = dynamic(() => import('./content'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-amber-400 font-bold animate-pulse">Loading QC Report...</div>
    </div>
  ),
});

export default function QCPageWrapper() {
  return <QCPage />;
}
