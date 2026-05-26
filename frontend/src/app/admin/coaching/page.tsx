'use client';
import dynamic from 'next/dynamic';

const CoachingDashboard = dynamic(() => import('./content'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen bg-slate-50 p-12 flex items-center justify-center">
      <div className="text-slate-400 font-medium animate-pulse">Loading Coaching Dashboard...</div>
    </div>
  ),
});

export default function CoachingPage() {
  return <CoachingDashboard />;
}
