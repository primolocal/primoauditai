'use client';
import dynamic from 'next/dynamic';

const ParserValidationPage = dynamic(() => import('./content'), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
      <div className="text-cyan font-bold animate-pulse">Loading Parser Validation...</div>
    </div>
  ),
});

export default function ParserValidationPageWrapper() {
  return <ParserValidationPage />;
}
