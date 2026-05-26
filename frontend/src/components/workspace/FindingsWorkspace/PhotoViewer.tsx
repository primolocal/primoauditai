"use client";
import React, { useState } from "react";
import { PhotoEvidence } from "@/types/claim";
import { API_BASE } from "@/lib/api";

export const PhotoViewer: React.FC<{ photos: PhotoEvidence[] }> = ({ photos }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [zoom, setZoom] = useState(1);

    if (photos.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 mt-4 bg-white border border-dashed border-slate-300 rounded shadow-sm text-slate-500">
                <span className="text-4xl mb-2 grayscale opacity-50">📷</span>
                <span className="text-sm font-bold">No Photos Available</span>
                <span className="text-xs mt-1">This claim package does not contain any images.</span>
            </div>
        );
    }

    const currentPhoto = photos[currentIndex];

    const nextPhoto = () => {
        setCurrentIndex((prev) => (prev + 1) % photos.length);
        setZoom(1);
    };

    const prevPhoto = () => {
        setCurrentIndex((prev) => (prev - 1 + photos.length) % photos.length);
        setZoom(1);
    };

    return (
        <div className="flex flex-col h-[700px] w-full bg-slate-900 rounded overflow-hidden shadow-md mt-4">
            {/* Top Bar: Labels & Meta */}
            <div className="h-12 bg-slate-800 text-slate-200 px-4 flex items-center justify-between border-b border-slate-700 shrink-0">
                <div className="flex flex-col">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Filename</span>
                    <span className="text-xs font-mono font-bold truncate max-w-[300px]">
                        {currentPhoto.url ? currentPhoto.url.split('/').pop() : 'Evidence Image'}
                    </span>
                </div>
                <div className="flex gap-2">
                    {(currentPhoto as any).ai_labels?.map((lbl: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 bg-blue-900 border border-blue-700 text-blue-200 text-[9px] uppercase font-bold tracking-widest rounded">
                            {lbl}
                        </span>
                    ))}
                    {!((currentPhoto as any).ai_labels?.length) && (
                        <span className="px-2 py-0.5 bg-slate-700 text-slate-400 text-[9px] uppercase font-bold tracking-widest rounded border border-slate-600">
                            Unlabeled
                        </span>
                    )}
                </div>
            </div>

            {/* Main Image Viewer */}
            <div className="flex-1 relative flex items-center justify-center overflow-hidden bg-black group selection:bg-transparent">
                <button 
                    onClick={prevPhoto}
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-white/20 transition-colors z-10 opacity-0 group-hover:opacity-100"
                >
                    ◄
                </button>
                
                <div 
                    className="w-full h-full flex items-center justify-center overflow-auto custom-scrollbar"
                    onClick={() => setZoom(z => z === 1 ? 2 : 1)}
                >
                    <img 
                        src={`${API_BASE}${currentPhoto.url}`} 
                        alt="Evidence"
                        className="object-contain transition-transform duration-200 origin-center cursor-zoom-in"
                        style={{ transform: `scale(${zoom})`, maxHeight: zoom === 1 ? '100%' : 'none', maxWidth: zoom === 1 ? '100%' : 'none' }}
                        onError={(e) => { e.currentTarget.src = 'https://placehold.co/800x600/1e293b/475569?text=Image+Unavailable'; }}
                    />
                </div>

                <button 
                    onClick={nextPhoto}
                    className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-white/20 transition-colors z-10 opacity-0 group-hover:opacity-100"
                >
                    ►
                </button>

                {/* Zoom Indicator overlay */}
                <div className="absolute bottom-4 right-4 bg-black/60 text-white text-[10px] uppercase font-bold tracking-widest px-2 py-1 rounded backdrop-blur border border-white/10 pointer-events-none">
                    Zoom: {Math.round(zoom * 100)}%
                </div>
            </div>

            {/* Thumbnail Strip */}
            <div className="h-24 bg-slate-800 border-t border-slate-700 p-2 flex gap-2 overflow-x-auto custom-scrollbar shrink-0">
                {photos.map((p, idx) => (
                    <div 
                        key={p.id}
                        onClick={() => { setCurrentIndex(idx); setZoom(1); }}
                        className={`h-full aspect-square shrink-0 rounded overflow-hidden cursor-pointer border-2 transition-all ${
                            idx === currentIndex ? 'border-blue-500 opacity-100 outline outline-2 outline-blue-500/30' : 'border-transparent opacity-60 hover:opacity-100 hover:border-slate-500'
                        }`}
                    >
                        <img 
                            src={`${API_BASE}${p.thumbnail_url || p.url}`} 
                            alt={`Thumb ${idx}`}
                            className="w-full h-full object-cover"
                            onError={(e) => { e.currentTarget.src = 'https://placehold.co/100x100/1e293b/475569?text=Error'; }}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
};
