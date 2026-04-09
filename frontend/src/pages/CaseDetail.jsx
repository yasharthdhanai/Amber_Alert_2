import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Video, UploadCloud, Map, AlertCircle, Camera, Search, UserCheck } from 'lucide-react';
import { cn } from '../lib/utils';

export default function CaseDetail() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('matches');

  // Dummy data matched with Dashboard layout visually
  const caseData = {
    id: caseId,
    child_name: caseId === "MCF-2024-001" ? "Aarav Sharma" : "Priya Patel",
    age: 6,
    status: "active",
    image_url: caseId === "MCF-2024-001" ? "https://images.unsplash.com/photo-1543332143-4e8c27e3256f?w=400&q=80" : "https://images.unsplash.com/photo-1514036783265-fba9577fc473?w=400&q=80"
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 max-w-7xl mx-auto">
      
      {/* Top Breadcrumb Nav */}
      <button 
        onClick={() => navigate(-1)}
        className="flex items-center text-slate-400 hover:text-emerald-400 mb-6 transition-colors font-medium text-sm group"
      >
        <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
        Back to Dashboard
      </button>

      {/* Case Header Profile */}
      <div className="glass-panel rounded-3xl p-8 mb-8 flex flex-col md:flex-row items-center md:items-start gap-8 relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute -top-32 -left-32 w-64 h-64 bg-emerald-500/20 rounded-full blur-[80px]" />
        
        <div className="relative">
          <div className="w-32 h-32 md:w-48 md:h-48 rounded-2xl overflow-hidden border-2 border-white/10 shadow-2xl z-10">
            <img src={caseData.image_url} alt="Child Profile" className="w-full h-full object-cover" />
          </div>
          <div className="absolute -bottom-3 -right-3 bg-emerald-500 p-2 rounded-xl shadow-lg border border-emerald-400">
            <UserCheck className="w-6 h-6 text-slate-900" />
          </div>
        </div>

        <div className="flex-1 space-y-4 text-center md:text-left z-10">
          <div className="flex items-center justify-center md:justify-start space-x-3">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white">{caseData.child_name}</h1>
            <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Active Case
            </span>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-4 border-t border-white/5">
            <div>
              <p className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-1">FIR Number</p>
              <p className="font-mono text-sm">{caseData.id}</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-1">Age</p>
              <p className="font-medium">{caseData.age} Years Old</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-1">Reported Missing</p>
              <p className="font-medium text-amber-400">Nov 15, 2024</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-1">Location Radius</p>
              <p className="font-medium flex items-center"><Map className="w-4 h-4 mr-1 text-slate-400" /> Howrah Station</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-4 mb-8 pb-4 border-b border-white/10 overflow-x-auto">
        {[
          { id: 'matches', label: "Found Matches (3)", icon: Search },
          { id: 'upload', label: "Upload CCTV", icon: UploadCloud },
          { id: 'live', label: "Live RTSP Monitoring", icon: Camera },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center px-5 py-3 rounded-xl font-medium transition-all duration-300 whitespace-nowrap",
              activeTab === tab.id 
                ? "bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-400 border border-emerald-500/30" 
                : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent"
            )}
          >
            <tab.icon className="w-5 h-5 mr-2" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content Areas */}
      <div className="mb-12">
        
        {/* MATCHES VIEW */}
        {activeTab === 'matches' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Scaffold Evidence Card */}
            <div className="glass-panel p-2 rounded-2xl group cursor-pointer hover:border-emerald-500/40 transition-colors">
              <div className="relative rounded-xl overflow-hidden h-48 bg-slate-900 border border-white/5">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-emerald-500/50 flex flex-col items-center">
                    <Video className="w-8 h-8 mb-2 opacity-50" />
                    <span className="text-xs uppercase tracking-widest font-semibold text-slate-500">SIMULATED MASK OVERLAY</span>
                  </div>
                </div>
                {/* Dummy layout for visual mask */}
                <div className="absolute top-8 left-12 w-24 h-48 bg-emerald-500/30 border-2 border-emerald-400 rounded-lg backdrop-blur-sm z-10" />
                
                <div className="absolute bottom-3 left-3 right-3 flex justify-between items-center z-20">
                  <span className="bg-red-500/80 text-white text-xs font-bold px-2 py-1 rounded backdrop-blur-md">98.2% Match</span>
                  <span className="bg-black/60 text-white text-xs font-mono px-2 py-1 rounded backdrop-blur-md">14:32:05</span>
                </div>
              </div>
              <div className="p-4 space-y-2">
                <h3 className="font-semibold text-white">Platform 3 - Camera C4</h3>
                <p className="text-sm text-slate-400">Processed from file: <span className="font-mono text-xs">howrah_pl3_nov15.mp4</span></p>
              </div>
            </div>
            
            {/* Action Card: Generate PDF */}
            <div className="glass-panel border-dashed border-2 border-slate-700 hover:border-emerald-500/50 flex flex-col items-center justify-center p-6 rounded-2xl text-center transition-colors cursor-pointer group">
              <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mb-4 group-hover:bg-emerald-500/20 group-hover:scale-110 transition-all duration-500">
                <AlertCircle className="w-8 h-8 text-slate-400 group-hover:text-emerald-400" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Export Court Report</h3>
              <p className="text-sm text-slate-400 mb-6 px-4">Generate a 100% offline, court-admissible PDF combining SAM 3.1 masks and timestamps.</p>
              <button className="glass-button px-6 py-2 rounded-full text-sm font-semibold shadow-lg">Download PDF</button>
            </div>
          </div>
        )}

        {/* UPLOAD VIEW */}
        {activeTab === 'upload' && (
           <div className="glass-panel border-dashed border-2 border-emerald-500/30 rounded-3xl p-12 flex flex-col items-center justify-center text-center bg-emerald-950/10">
              <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6">
                <UploadCloud className="w-10 h-10 text-emerald-400 animate-bounce" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">Drag & Drop CCTV Footage</h2>
              <p className="text-slate-400 max-w-md mb-8">
                Upload raw MP4, MKV, or AVI footage. Our offline Celery workers will slice, orient, and extract InsightFace match queries instantly.
              </p>
              <div className="flex space-x-4">
                <button className="glass-button-primary px-8 py-3 rounded-xl transition-transform hover:scale-105">Select File (max 10GB)</button>
              </div>
           </div>
        )}

        {/* RTSP VIEW */}
        {activeTab === 'live' && (
           <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
             <div className="glass-panel rounded-3xl p-8">
                <h3 className="text-xl font-bold text-white mb-6 flex items-center">
                  <Camera className="mr-3 w-6 h-6 text-emerald-400" /> Register RTSP Stream
                </h3>
                <div className="space-y-5">
                  <div>
                    <label className="block text-xs uppercase font-semibold text-slate-500 tracking-wider mb-2">Camera Location Name</label>
                    <input type="text" className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500/50" placeholder="e.g. Traffic Cam Intersection 4" />
                  </div>
                  <div>
                    <label className="block text-xs uppercase font-semibold text-slate-500 tracking-wider mb-2">Network RTSP Stream URL</label>
                    <input type="text" className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500/50 font-mono text-sm" placeholder="rtsp://admin:pass@192.168.1.55:554/stream1" />
                  </div>
                  <button className="glass-button-primary w-full py-4 rounded-xl mt-4">Connect & Analyze Stream</button>
                </div>
             </div>
             
             <div className="glass-panel rounded-3xl border-slate-800 p-8 flex flex-col justify-center items-center text-center">
                 <div className="relative">
                   <div className="w-24 h-24 rounded-full border-4 border-slate-800 border-t-emerald-500 animate-spin" />
                   <div className="w-max absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                      <Camera className="w-8 h-8 text-slate-600" />
                   </div>
                 </div>
                 <p className="mt-8 text-lg font-medium text-slate-400">Waiting for Stream Registration...</p>
                 <p className="text-sm text-slate-600 mt-2">Connect a stream to monitor live inference.</p>
             </div>
           </div>
        )}
      </div>

    </div>
  );
}
