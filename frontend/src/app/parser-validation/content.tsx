'use client';

import { useState } from 'react';
import { UploadCloud, CheckCircle2, AlertTriangle, FileBox, Car, DollarSign, Target, List, Archive, Code } from 'lucide-react';

export default function ParserValidationContent() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [qaData, setQaData] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSimulateUpload = async (file: File) => {
    setIsProcessing(true);
    setErrorMsg('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await fetch('/api/upload-ems', { method: 'POST', body: formData });
      const data = await res.json();
      
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Failed to parse file.');
      }
      
      setQaData(data);
    } catch (e: any) {
      setErrorMsg(e.message);
      setQaData(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => e.preventDefault();
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (!isProcessing && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleSimulateUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-primary font-sans p-8">
      
      <header className="mb-8 border-b border-[var(--border-muted)] pb-4">
        <h1 className="text-2xl font-bold flex items-center gap-3">
          <FileBox className="text-cyan" /> EMS Parser QA Dashboard
        </h1>
        <p className="text-secondary mt-1">Direct visibility into the Python extraction layer. Drop real CCC ZIP folders here.</p>
      </header>

      <div className="flex flex-col gap-8 max-w-7xl mx-auto">
        
        <div 
          className="bg-[var(--bg-panel)] border-2 border-dashed rounded-md p-10 text-center transition-colors hover:border-cyan cursor-pointer"
          style={{ borderColor: 'var(--border-muted)' }}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          {isProcessing ? (
             <div className="animate-pulse flex flex-col items-center">
               <UploadCloud size={48} className="text-cyan mb-4" />
               <p className="font-bold">Executing Python Module...</p>
             </div>
          ) : (
             <div className="flex flex-col items-center">
               <UploadCloud size={48} className="text-secondary mb-4" />
               <p className="font-bold">Drag and Drop EMS Zip</p>
               <p className="text-xs text-secondary mt-2">Will trigger `/api/upload-ems` returning raw metadata.</p>
             </div>
          )}
        </div>

        {errorMsg && (
          <div className="bg-[var(--status-fail)] bg-opacity-20 border border-[var(--status-fail)] text-[var(--status-fail)] p-4 rounded-md flex items-center gap-2">
             <AlertTriangle size={18} />
             <span className="font-bold">{errorMsg}</span>
          </div>
        )}

        {qaData && (
          <div className="grid grid-cols-12 gap-6">
             
             <div className="col-span-12 md:col-span-4 flex flex-col gap-6">
                
                <div className="bg-[var(--bg-panel)] border border-[var(--border-muted)] rounded-md overflow-hidden">
                   <div className="bg-[var(--bg-secondary)] border-b border-[var(--border-muted)] p-3 flex items-center gap-2 font-bold uppercase text-xs tracking-wider">
                     <Target size={14} className="text-cyan" /> Parse Status
                   </div>
                   <div className="p-4 flex flex-col gap-3">
                     <div className="flex items-center justify-between">
                       <span className="text-secondary">Extraction</span>
                       <span className="text-[var(--status-pass)] font-bold flex items-center gap-1"><CheckCircle2 size={14}/> SUCCESS</span>
                     </div>
                     <div className="flex items-center justify-between">
                       <span className="text-secondary">Line Count</span>
                       <span className="font-mono text-bright bg-[var(--bg-primary)] px-2 py-0.5 rounded border border-[var(--border-muted)]">{qaData.line_count}</span>
                     </div>
                     <div className="flex items-center justify-between">
                       <span className="text-secondary">Warnings Flags</span>
                       <span className="font-mono bg-[var(--bg-primary)] px-2 py-0.5 rounded border border-[var(--border-muted)]" style={{ color: qaData.warnings.length > 0 ? 'var(--status-warn)' : 'var(--status-pass)' }}>
                         {qaData.warnings.length}
                       </span>
                     </div>
                   </div>
                </div>

                {qaData.warnings.length > 0 && (
                  <div className="bg-[var(--bg-panel)] border border-[var(--status-warn)] border-opacity-30 rounded-md overflow-hidden">
                     <div className="bg-[var(--bg-secondary)] border-b border-[var(--status-warn)] border-opacity-30 p-3 flex items-center gap-2 font-bold uppercase text-xs tracking-wider text-[var(--status-warn)]">
                       <AlertTriangle size={14} /> Parser Warnings
                     </div>
                     <ul className="p-4 flex flex-col gap-2 text-sm text-[var(--status-warn)]">
                       {qaData.warnings.map((w: string, i: number) => (
                         <li key={i} className="flex gap-2"><span className="opacity-50">•</span> {w}</li>
                       ))}
                     </ul>
                  </div>
                )}
             </div>

             <div className="col-span-12 md:col-span-8 grid grid-cols-2 gap-6">
               <div className="bg-[var(--bg-panel)] border border-[var(--border-muted)] rounded-md overflow-hidden">
                   <div className="bg-[var(--bg-secondary)] border-b border-[var(--border-muted)] p-3 flex items-center gap-2 font-bold uppercase text-xs tracking-wider">
                     <Car size={14} className="text-cyan" /> Vehicle Extraction
                   </div>
                   <div className="p-4 grid grid-cols-2 gap-y-4 gap-x-2 text-sm">
                     <div className="flex flex-col"><span className="text-[10px] text-secondary uppercase tracking-widest">Year</span><span className="font-medium">{qaData.vehicle?.year || '--'}</span></div>
                     <div className="flex flex-col"><span className="text-[10px] text-secondary uppercase tracking-widest">Make</span><span className="font-medium">{qaData.vehicle?.make || '--'}</span></div>
                     <div className="flex flex-col"><span className="text-[10px] text-secondary uppercase tracking-widest">Model</span><span className="font-medium">{qaData.vehicle?.model || '--'}</span></div>
                     <div className="flex flex-col"><span className="text-[10px] text-secondary uppercase tracking-widest">Trim</span><span className="font-medium">{qaData.vehicle?.trim || '--'}</span></div>
                     <div className="col-span-2 flex flex-col"><span className="text-[10px] text-secondary uppercase tracking-widest">VIN</span><span className="font-mono text-cyan">{qaData.vehicle?.vin || '--'}</span></div>
                   </div>
               </div>

               <div className="bg-[var(--bg-panel)] border border-[var(--border-muted)] rounded-md overflow-hidden flex flex-col">
                   <div className="bg-[var(--bg-secondary)] border-b border-[var(--border-muted)] p-3 flex items-center justify-between font-bold uppercase text-xs tracking-wider">
                     <span className="flex items-center gap-2"><DollarSign size={14} className="text-cyan" /> Estimate Totals</span>
                     <span className="font-mono text-bright text-sm">${qaData.totals?.total?.toFixed(2) || '0.00'}</span>
                   </div>
                   
                   <div className="p-4 grid grid-cols-2 gap-4 text-xs flex-grow content-start">
                     <div className="col-span-2 text-[10px] text-secondary uppercase tracking-widest border-b border-[var(--border-muted)] pb-1 mb-1">Tag Distribution</div>
                     {Object.entries(qaData.records_by_tag_counts || {}).map(([tag, count]) => (
                       <div key={tag} className="flex justify-between font-mono bg-[var(--bg-secondary)] px-2 py-1 rounded-sm border border-[var(--border-muted)]">
                         <span className="text-cyan">{tag}</span>
                         <span>{String(count)}</span>
                       </div>
                     ))}
                   </div>
               </div>
             </div>

             <div className="col-span-12 bg-[var(--bg-panel)] border border-[var(--border-muted)] rounded-md overflow-hidden mt-6">
                 <div className="bg-[var(--bg-secondary)] border-b border-[var(--border-muted)] p-3 flex items-center justify-between font-bold uppercase text-xs tracking-wider">
                   <span className="flex items-center gap-2"><Archive size={14} className="text-cyan" /> ZIP Extraction Manifest</span>
                   <span className="text-[10px] text-secondary">
                      {qaData.parsed_files_count} Parsed / {qaData.skipped_files_count} Skipped
                   </span>
                 </div>
                 <div className="overflow-x-auto">
                   <table className="w-full text-left text-xs whitespace-nowrap">
                     <thead className="bg-[#0B0F14] border-b border-[var(--border-muted)] text-[10px] uppercase tracking-wider text-secondary">
                       <tr>
                         <th className="p-3">File Name</th>
                         <th className="p-3">Size (B)</th>
                         <th className="p-3 text-center">Status</th>
                         <th className="p-3">Diagnostic Reason</th>
                       </tr>
                     </thead>
                     <tbody>
                       {qaData.zip_manifest.map((file: any, i: number) => (
                         <tr key={i} className="border-b border-[#1A222C] last:border-0 hover:bg-[#0B0F14] bg-[#121821]">
                           <td className="p-3 font-mono text-cyan">{file.name}</td>
                           <td className="p-3 text-secondary font-mono">{file.size}</td>
                           <td className="p-3 text-center">
                             {file.parsed ? <span className="text-[var(--status-pass)] font-bold">PARSED</span> : <span className="text-secondary opacity-50">SKIPPED</span>}
                           </td>
                           <td className="p-3 font-mono text-secondary max-w-[300px] truncate">{file.reason || '--'}</td>
                         </tr>
                       ))}
                     </tbody>
                   </table>
                 </div>
             </div>
             
             {qaData.zip_manifest.filter((f: any) => f.parsed && f.raw_preview?.length > 0).length > 0 && (
               <div className="col-span-12 bg-[var(--bg-panel)] border border-[var(--border-muted)] rounded-md overflow-hidden mt-2">
                   <div className="bg-[var(--bg-secondary)] border-b border-[var(--border-muted)] p-3 flex items-center justify-between font-bold uppercase text-xs tracking-wider">
                     <span className="flex items-center gap-2"><Code size={14} className="text-cyan" /> Raw Segment Previews (First 5 lines)</span>
                   </div>
                   <div className="p-4 flex flex-col gap-4 bg-[#0B0F14]">
                     {qaData.zip_manifest.filter((f: any) => f.parsed && f.raw_preview?.length > 0).map((file: any, i: number) => (
                       <div key={i} className="border border-[var(--border-muted)] rounded bg-[#121821]">
                         <div className="p-2 border-b border-[var(--border-muted)] text-[10px] font-mono text-cyan flex justify-between">
                           <span>{file.name}</span>
                         </div>
                         <div className="p-3 text-secondary font-mono text-xs overflow-x-auto break-all">
                           {file.raw_preview.map((line: string, lineIdx: number) => (
                             <div key={lineIdx} className="mb-1">{line}</div>
                           ))}
                         </div>
                       </div>
                     ))}
                   </div>
               </div>
             )}

             <div className="col-span-12 bg-[var(--bg-panel)] border border-[var(--border-muted)] rounded-md overflow-hidden mt-2">
                 <div className="bg-[var(--bg-secondary)] border-b border-[var(--border-muted)] p-3 flex items-center justify-between font-bold uppercase text-xs tracking-wider">
                   <span className="flex items-center gap-2"><List size={14} className="text-cyan" /> Normalized Lines Sample (Top 20)</span>
                 </div>
                 <div className="overflow-x-auto">
                   <table className="w-full text-left text-xs whitespace-nowrap">
                     <thead className="bg-[var(--bg-secondary)] border-b border-[var(--border-muted)] text-[10px] uppercase tracking-wider text-secondary">
                       <tr>
                         <th className="p-3 w-12 text-center">Line</th>
                         <th className="p-3">Record Type</th>
                         <th className="p-3">Description</th>
                         <th className="p-3 bg-black bg-opacity-20">Op / Part #</th>
                         <th className="p-3 text-right">Ext Price</th>
                       </tr>
                     </thead>
                     <tbody>
                       {qaData.sample_lines.map((line: any, i: number) => (
                         <tr key={i} className="border-b border-[var(--border-muted)] last:border-0 hover:bg-[var(--bg-hover)]">
                           <td className="p-3 font-mono text-secondary text-center">{line.line_number || '--'}</td>
                           <td className="p-3 font-bold text-cyan">{line.record_type}</td>
                           <td className="p-3 font-semibold truncate max-w-[200px]">{line.description || '--'}</td>
                           <td className="p-3 font-mono text-secondary bg-black bg-opacity-20">{line.op_code || line.part_number || '--'}</td>
                           <td className="p-3 font-mono text-right text-cyan">${parseFloat(line.total || line.unit_price || '0').toFixed(2)}</td>
                         </tr>
                       ))}
                       {qaData.sample_lines.length === 0 && (
                         <tr><td colSpan={5} className="p-8 text-center text-secondary">No line items populated in .lin extension.</td></tr>
                       )}
                     </tbody>
                   </table>
                 </div>
             </div>

          </div>
        )}
      </div>
    </div>
  );
}
