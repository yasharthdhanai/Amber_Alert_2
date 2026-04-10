import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Video, UploadCloud, Map, AlertCircle, Camera, Search, UserCheck, Loader2, CheckCircle2, Clock } from 'lucide-react';
import { cn } from '../lib/utils';
import { fetchCase, getCasePhotoUrl, fetchMatches, getMatchScreenshotUrl, uploadVideo, registerRtsp, fetchJobs } from '../lib/api';

export default function CaseDetail() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState('matches');
  const [caseData, setCaseData] = useState(null);
  const [matches, setMatches] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Upload State
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  // RTSP State
  const [rtspUrl, setRtspUrl] = useState('');
  const [cameraName, setCameraName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [rtspError, setRtspError] = useState('');

  useEffect(() => {
    loadData();
    // Poll for new matches and job progress every 3 seconds
    const interval = setInterval(() => {
      loadJobsAndMatches();
    }, 3000);
    return () => clearInterval(interval);
  }, [caseId]);

  async function loadData() {
    try {
      const data = await fetchCase(caseId);
      setCaseData(data);
      await loadJobsAndMatches();
    } catch (err) {
      console.error(err);
      navigate('/cases');
    } finally {
      setLoading(false);
    }
  }

  async function loadJobsAndMatches() {
    try {
      const [matchesRes, jobsRes] = await Promise.all([
        fetchMatches(caseId),
        fetchJobs(caseId)
      ]);
      setMatches(matchesRes);
      setJobs(jobsRes);
    } catch (err) {
      console.error("Failed to load dynamic data", err);
    }
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError('');
    try {
      await uploadVideo(caseId, file);
      // Immediately fetch jobs to show the new scanning job
      await loadJobsAndMatches();
      // Switch back to matches/jobs view automatically? Or remain on upload tab to see progress.
      // Let's stay, the progress bar will appear below.
    } catch (err) {
      setUploadError(err.message || "Failed to upload video");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRtspSubmit = async (e) => {
    e.preventDefault();
    if (!rtspUrl) return;

    setIsRegistering(true);
    setRtspError('');
    try {
      await registerRtsp(caseId, rtspUrl, cameraName || "Unknown Camera");
      setRtspUrl('');
      setCameraName('');
      await loadJobsAndMatches();
      // Switch to matches tab
      setActiveTab('matches');
    } catch (err) {
      setRtspError(err.message || "Failed to connect RTSP stream");
    } finally {
      setIsRegistering(false);
    }
  };

  if (loading || !caseData) {
    return (
      <div className="flex justify-center items-center h-full">
        <Loader2 className="w-12 h-12 animate-spin text-emerald-500" />
      </div>
    );
  }

  const activeJobs = jobs.filter(j => j.status === 'queued' || j.status === 'running' || j.status === 'retrying');

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 max-w-7xl mx-auto">
      
      {/* Top Breadcrumb Nav */}
      <button 
        onClick={() => navigate('/cases')}
        className="flex items-center text-slate-400 hover:text-emerald-400 mb-6 transition-colors font-medium text-sm group"
      >
        <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
        Back to Dashboard
      </button>

      {/* Case Header Profile */}
      <div className="glass-panel rounded-3xl p-8 mb-8 flex flex-col md:flex-row items-center md:items-start gap-8 relative overflow-hidden border border-white/5 shadow-2xl">
        <div className="absolute -top-32 -left-32 w-64 h-64 bg-emerald-500/20 rounded-full blur-[80px]" />
        
        <div className="relative">
          <div className="w-32 h-32 md:w-48 md:h-48 rounded-2xl overflow-hidden border-2 border-white/10 shadow-2xl z-10 bg-slate-900">
            <img src={caseData.reference_photo || getCasePhotoUrl(caseData.id)} alt={caseData.child_name} className="w-full h-full object-cover" />
          </div>
          <div className="absolute -bottom-3 -right-3 bg-emerald-500 p-2 rounded-xl shadow-lg border border-emerald-400">
            <UserCheck className="w-6 h-6 text-slate-900" />
          </div>
        </div>

        <div className="flex-1 space-y-4 text-center md:text-left z-10 w-full">
          <div className="flex flex-col md:flex-row md:items-center justify-between w-full">
            <div className="flex items-center space-x-3 mb-4 md:mb-0">
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white">{caseData.child_name}</h1>
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border ${(caseData.status || 'active') === 'active' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-slate-500/20 text-slate-400 border-slate-500/30'}`}>
                {(caseData.status || 'active')} Case
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-4 border-t border-white/5 w-full">
            <div>
              <p className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-1">FIR Number</p>
              <p className="font-mono text-sm text-slate-200">{caseData.case_number}</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-1">Age</p>
              <p className="font-medium text-slate-200">{caseData.child_age} Years</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-1">Reported Missing</p>
              <p className="font-medium text-amber-400">{caseData.last_seen_date ? new Date(caseData.last_seen_date).toLocaleDateString() : 'Unknown'}</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-1">Location Radius</p>
              <p className="font-medium flex items-center text-slate-200 truncate pr-4" title={caseData.last_seen_place}><Map className="w-4 h-4 mr-1 text-slate-400 flex-shrink-0" /> {caseData.last_seen_place || 'Unknown'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Dynamic Job Progress Trackers (Shows up globally if active jobs exist) */}
      {activeJobs.length > 0 && (
        <div className="mb-8 space-y-3">
          {activeJobs.map(job => (
            <div key={job.id} className="glass-panel p-4 rounded-xl flex items-center justify-between shadow-lg border border-emerald-500/30 relative overflow-hidden">
               <div className="absolute bottom-0 left-0 h-1 bg-emerald-500 transition-all duration-1000 ease-in-out" style={{ width: `${job.progress_pct}%` }} />
               <div className="flex items-center">
                 {job.job_type === 'scan_video' ? <Video className="w-5 h-5 text-emerald-400 mr-3 animate-pulse" /> : <Camera className="w-5 h-5 text-emerald-400 mr-3 animate-pulse" />}
                 <div>
                   <p className="font-medium text-sm text-slate-200">
                     {job.job_type === 'scan_video' ? 'Batch Video ML Analysis Running...' : 'RTSP Live Stream Monitor Active'}
                   </p>
                   <p className="text-xs text-slate-400 font-mono mt-1">Job ID: {job.id.substring(0,8)} | Status: {job.status.toUpperCase()}</p>
                 </div>
               </div>
               <div className="flex flex-col items-end">
                 <span className="text-lg font-bold text-emerald-400">{job.progress_pct}%</span>
                 <span className="text-xs text-slate-400">{job.frames_done} / {job.frames_total || '?'} frames</span>
               </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-4 mb-8 pb-4 border-b border-white/10 overflow-x-auto">
        {[
          { id: 'matches', label: `Matches Found (${matches.length})`, icon: Search },
          { id: 'upload', label: "Upload CCTV", icon: UploadCloud },
          { id: 'live', label: "Live RTSP Stream", icon: Camera },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center px-5 py-3 rounded-xl font-medium transition-all duration-300 whitespace-nowrap",
              activeTab === tab.id 
                ? "bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-400 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]" 
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
          <div className="space-y-6">
            <div className="flex items-centerjustify-between">
              <h2 className="text-xl font-bold text-white flex items-center">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 mr-2" /> AI Match Logs
              </h2>
            </div>
            
            {matches.length === 0 ? (
              <div className="glass-panel p-16 text-center rounded-2xl border-dashed border-2 border-white/10">
                <Search className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400 text-lg">No matches found for this case yet.</p>
                <p className="text-slate-500 text-sm mt-2">Upload CCTV footage or register an RTSP stream to begin tracking.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {matches.map(m => (
                  <div key={m.id} className="glass-panel p-2 rounded-2xl group cursor-pointer hover:border-emerald-500/40 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 bg-slate-900 border border-white/10">
                    <div className="relative rounded-xl overflow-hidden aspect-video bg-black/50 border border-white/5 flex items-center justify-center group-hover:border-emerald-500/30">
                      
                      <img 
                        src={m.screenshot_path || getMatchScreenshotUrl(caseId, m.id)} 
                        alt="Match Snapshot"
                        className="w-full h-full object-contain"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                      
                      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/80 pointer-events-none" />
                      
                      <div className="absolute top-3 left-3 bg-red-600 border border-red-500 px-2 py-0.5 rounded shadow-lg">
                        <span className="text-white text-xs font-bold font-mono tracking-widest">{m.source_type === 'rtsp' ? 'LIVE ALERT' : 'DETECTION'}</span>
                      </div>

                      <div className="absolute bottom-3 left-3 right-3 flex justify-between items-center z-20">
                        <span className="bg-emerald-500/80 text-white text-xs font-bold px-2 py-1 rounded backdrop-blur-md shadow-lg border border-emerald-400">{(m.confidence_score * 100).toFixed(1)}% Match</span>
                        <span className="bg-slate-800/80 text-slate-200 text-xs font-mono px-2 py-1 rounded backdrop-blur-md border border-slate-700">{m.timestamp_display}</span>
                      </div>
                    </div>
                    
                    <div className="p-4 space-y-2 relative">
                      <h3 className="font-semibold text-white tracking-tight truncate pr-4" title={m.video_source}>{m.video_source}</h3>
                      <div className="flex items-center text-xs text-slate-400">
                        <Clock className="w-3.5 h-3.5 mr-1 text-slate-500" />
                        Detected: {new Date(m.detected_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* UPLOAD VIEW */}
        {activeTab === 'upload' && (
           <div className="glass-panel border-dashed border-2 border-emerald-500/30 rounded-3xl p-12 flex flex-col items-center justify-center text-center bg-gradient-to-b from-transparent to-emerald-950/20">
              
              <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6 border border-emerald-500/20">
                <UploadCloud className="w-10 h-10 text-emerald-400 animate-bounce" />
              </div>
              
              <h2 className="text-3xl font-bold text-white mb-3">Upload Offline CCTV Footage</h2>
              <p className="text-slate-400 max-w-lg mb-8 leading-relaxed">
                Upload raw MP4, MKV, or AVI footage from local DVRs. Our offline Celery workers will extract frames and execute high-speed InsightFace matrix comparisons securely.
              </p>
              
              {uploadError && <div className="mb-6 bg-red-500/20 text-red-300 font-medium px-4 py-2 rounded-lg border border-red-500/30 max-w-md w-full">{uploadError}</div>}
              
              <input 
                type="file" 
                accept="video/*" 
                ref={fileInputRef}
                onChange={handleFileUpload}
                className="hidden" 
              />
              
              <button 
                disabled={isUploading}
                onClick={() => fileInputRef.current?.click()}
                className="glass-button-primary px-8 py-3 rounded-xl transition-transform hover:scale-105 shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {isUploading ? <><Loader2 className="w-5 h-5 mr-3 animate-spin"/> Queuing Task...</> : 'Select Video File (max 10GB)'}
              </button>
           </div>
        )}

        {/* RTSP VIEW */}
        {activeTab === 'live' && (
           <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
             <div className="glass-panel rounded-3xl p-8 border border-white/10 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                   <Camera className="w-32 h-32 text-emerald-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-6 flex items-center relative z-10">
                  <Camera className="mr-3 w-6 h-6 text-emerald-400" /> Register Live Stream
                </h3>
                
                {rtspError && <div className="mb-6 bg-red-500/20 text-red-300 font-medium px-4 py-2 rounded-lg border border-red-500/30">{rtspError}</div>}

                <form onSubmit={handleRtspSubmit} className="space-y-5 relative z-10">
                  <div>
                    <label className="block text-xs uppercase font-semibold text-slate-500 tracking-wider mb-2">Camera Location Descriptor</label>
                    <input required value={cameraName} onChange={(e)=>setCameraName(e.target.value)} type="text" className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-4 py-3 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500/50 backdrop-blur" placeholder="e.g. VT Station Concourse Gate 1" />
                  </div>
                  <div>
                    <label className="block text-xs uppercase font-semibold text-slate-500 tracking-wider mb-2">Network RTSP URL</label>
                    <input required value={rtspUrl} onChange={(e)=>setRtspUrl(e.target.value)} type="text" className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-4 py-3 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500/50 font-mono text-sm backdrop-blur" placeholder="rtsp://admin:pass@192.168.1.55:554/stream1" />
                  </div>
                  <button disabled={isRegistering} type="submit" className="glass-button-primary w-full py-4 rounded-xl mt-4 shadow-lg disabled:opacity-50 flex justify-center items-center font-bold tracking-wide">
                    {isRegistering ? <><Loader2 className="w-5 h-5 mr-3 animate-spin"/> Contacting Server...</> : 'Connect & Analyze Stream'}
                  </button>
                </form>
             </div>
             
             {/* Decorative placeholder for live view */}
             <div className="glass-panel rounded-3xl border-dashed border-2 border-slate-700 hover:border-emerald-500/30 transition-colors p-8 flex flex-col justify-center items-center text-center bg-slate-900/50">
                 <div className="relative">
                   <div className="w-24 h-24 rounded-full border-4 border-slate-800 border-t-emerald-500 animate-spin" />
                   <div className="w-max absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                      <Camera className="w-8 h-8 text-slate-500" />
                   </div>
                 </div>
                 <p className="mt-8 text-lg font-medium text-slate-300">Awaiting Subnet Stream Connection...</p>
                 <p className="text-sm text-slate-500 mt-2 max-w-sm mx-auto">Register an RTSP URL above to spin up a Celery worker dedicated to monitoring this perimeter in real-time.</p>
             </div>
           </div>
        )}
      </div>
    </div>
  );
}
