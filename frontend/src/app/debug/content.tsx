'use client';
import { useState } from 'react';

export default function DebugContent() {
   const [result, setResult] = useState<any>(null);
   const [loading, setLoading] = useState(false);

   const handleDrop = async (e: any) => {
      e.preventDefault();
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;

      setLoading(true);
      const fd = new FormData();
      fd.append('file', file);
      
      try {
         const res = await fetch('/api/debug', { method: 'POST', body: fd });
         const data = await res.json();
         setResult(data);
      } catch (err) {
         setResult({ error: String(err) });
      } finally {
         setLoading(false);
      }
   };

   return (
      <div className="p-8 min-h-screen text-white font-mono text-sm" style={{ backgroundColor: '#0B0F14' }}>
         <h1 className="text-xl font-bold mb-4 flex items-center gap-3">
             <span className="bg-cyan-500 w-3 h-3 block rounded-full"></span> 
             Raw Python Engine Data Monitor
         </h1>
         <p className="text-gray-400 mb-8 border-b border-gray-800 pb-4">Strictly prints standard output schema extraction bypassing Next.JS UI manipulation mappings. Used strictly as validation layer.</p>

         <div 
            onDrop={handleDrop} 
            onDragOver={e => e.preventDefault()}
            className="border-2 border-dashed border-cyan-800 hover:border-cyan-400 transition-colors p-16 text-center mb-8 rounded cursor-pointer flex flex-col items-center justify-center"
            style={{ backgroundColor: '#111820' }}
         >
            {loading ? (
                <div className="flex flex-col items-center gap-4">
                   <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin"></div>
                   <span className="text-cyan-400 font-bold tracking-widest text-lg">SPINNING UP PYTHON PARSER...</span>
                </div>
            ) : (
                <div className="flex flex-col items-center gap-2">
                   <span className="text-cyan-500 font-bold tracking-widest text-lg uppercase">Drop CCC EMS Target Zip Here</span>
                   <span className="text-gray-500">Initiates strict stdout terminal readout format parsing</span>
                </div>
            )}
         </div>

         {result && (
            <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between bg-black p-3 rounded-t border border-gray-800 border-b-0">
                   <span className="font-bold text-cyan-500 uppercase tracking-widest text-xs">Extraction Payload Log</span>
                   <span className="text-gray-500 text-xs">Response Code 200 {result.warnings?.length > 0 && <span className="text-yellow-500 ml-2">({result.warnings.length} Warnings)</span>}</span>
                </div>
                <pre className="bg-[#11161d] p-6 rounded-b border border-gray-800 text-[#4bc060] overflow-x-auto whitespace-pre-wrap max-h-[800px] overflow-y-auto custom-scroll shadow-inner">
                   {JSON.stringify(result, null, 2)}
                </pre>
            </div>
         )}
      </div>
   )
}
