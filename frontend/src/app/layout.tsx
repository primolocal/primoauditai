import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PrimoAuditAI - Audit Copilot',
  description: 'Enterprise human-in-the-loop audit copilot for auto damage estimates.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-slate-50 text-slate-900 antialiased">
        <div className="app-container">
          {children}
        </div>
      </body>
    </html>
  );
}
