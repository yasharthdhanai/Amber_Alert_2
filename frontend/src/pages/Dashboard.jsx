import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, MapPin, User, Plus, FileVideo, Activity, X, Loader2 } from 'lucide-react';
import { fetchCases, getCasePhotoUrl, createCase } from '../lib/api';

export default function Dashboard() {
  const navigate = useNavigate();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Form State
  const [formData, setFormData] = useState({
    case_number: '',
    child_name: '',
    child_age: '',
    last_seen_place: '',
    last_seen_date: '',
    description: '',
  });
  const [photo, setPhoto] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadCases();
    // Poll every 5 seconds for updates (matches found, etc.)
    const interval = setInterval(loadCases, 5000);
    return () => clearInterval(interval);
  }, []);

  async function loadCases() {
    try {
      const data = await fetchCases();
      setCases(data);
    } catch (err) {
      console.error("Failed to load cases", err);
    } finally {
      setLoading(false);
    }
  }

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handlePhotoChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setPhoto(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!photo) {
      setError("Reference photo is required");
      return;
    }
    
    setSubmitting(true);
    setError('');
    
    const data = new FormData();
    Object.keys(formData).forEach(key => {
      data.append(key, formData[key]);
    });
    data.append('reference_photo', photo);

    try {
      const newCase = await createCase(data);
      if (!newCase.has_embedding) {
        // Warning logic if embedding failed, but case created
        alert("Case created, but ML engine failed to extract face embedding. You may need to retry photo upload later.");
      }
      setIsModalOpen(false);
      setFormData({
        case_number: '', child_name: '', child_age: '', last_seen_place: '', last_seen_date: '', description: ''
      });
      setPhoto(null);
      loadCases();
    } catch (err) {
      setError(err.message || 'Failed to create case');
    } finally {
      setSubmitting(false);
    }
  };

  // Stats derived from cases
  const totalMatches = cases.reduce((acc, c) => acc + (c.total_matches || 0), 0);
  const totalVideos = cases.reduce((acc, c) => acc + (c.videos_analyzed || 0), 0);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 relative">
      
      {/* Header Section */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold mb-2">Active Cases</h1>
          <p className="text-slate-400">Monitoring real-time CCTV feeds and processing manual uploads.</p>
        </div>
        
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center px-6 py-3 rounded-lg glass-button-primary"
        >
          <Plus className="w-5 h-5 mr-2" />
          New Case
        </button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: "Active Cases", value: cases.length.toString(), icon: Activity, color: "text-emerald-400" },
          { label: "Videos Scanned", value: totalVideos.toString(), icon: FileVideo, color: "text-blue-400" },
          { label: "Total Matches", value: totalMatches.toString(), icon: User, color: "text-purple-400" },
        ].map((stat, idx) => (
          <div key={idx} className="glass-panel p-6 rounded-2xl flex items-center shadow-lg hover:-translate-y-1 transition-transform duration-300">
            <div className={`p-4 rounded-xl bg-white/5 mr-5 border border-white/5 ${stat.color}`}>
              <stat.icon className="w-6 h-6" />
            </div>
            <div>
              <p className="text-slate-400 text-sm font-medium">{stat.label}</p>
              <h3 className="text-3xl font-bold tracking-tight">{stat.value}</h3>
            </div>
          </div>
        ))}
      </div>

      {/* Case Grid */}
      {loading ? (
        <div className="flex justify-center items-center py-20">
          <Loader2 className="w-10 h-10 animate-spin text-emerald-500" />
        </div>
      ) : cases.length === 0 ? (
        <div className="glass-panel p-16 text-center rounded-2xl border-dashed border-2 border-white/10">
          <p className="text-slate-400 text-lg mb-4">No active cases registered.</p>
          <button onClick={() => setIsModalOpen(true)} className="text-emerald-400 hover:text-emerald-300 font-medium font-bold">Register a missing child now &rarr;</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-8 pt-4">
          {cases.map(c => (
            <div 
              key={c.id} 
              onClick={() => navigate(`/cases/${c.id}`)}
              className="group relative glass-panel rounded-2xl overflow-hidden cursor-pointer hover:shadow-2xl hover:shadow-emerald-500/10 transition-all duration-500 border border-white/5 hover:border-emerald-500/30"
            >
              {/* Image Header */}
              <div className="h-48 w-full relative overflow-hidden bg-slate-900 border-b border-white/5">
                <div className="absolute inset-0 bg-gradient-to-t from-slate-900 to-transparent z-10 opacity-90" />
                <img 
                  src={c.reference_photo || getCasePhotoUrl(c.id)} 
                  className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-700"
                  alt={c.child_name} 
                  onError={(e) => { e.target.src = "https://images.unsplash.com/photo-1543332143-4e8c27e3256f?w=400&q=80"; }} // Fallback
                />
                <div className="absolute bottom-4 left-5 z-20 flex justify-between items-end w-[calc(100%-40px)]">
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 flex items-center">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
                        {c.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-slate-300 font-medium">{c.case_number}</span>
                    </div>
                    <h2 className="text-2xl font-bold text-white">{c.child_name}, <span className="opacity-75 text-lg">{c.child_age}</span></h2>
                  </div>
                </div>
              </div>

              {/* Details Body */}
              <div className="p-5 space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center text-sm text-slate-400">
                    <Clock className="w-4 h-4 mr-3 text-slate-500 flex-shrink-0" />
                    <span>Last seen <strong className="text-slate-200">{c.last_seen_date || 'Unknown'}</strong></span>
                  </div>
                  <div className="flex items-center text-sm text-slate-400">
                    <MapPin className="w-4 h-4 mr-3 text-slate-500 flex-shrink-0" />
                    <span className="truncate">{c.last_seen_place || 'Unknown'}</span>
                  </div>
                </div>

                {/* Match Indicator */}
                <div className={`mt-4 pt-4 border-t border-white/10 flex items-center justify-between ${c.total_matches > 0 ? "text-emerald-400" : "text-slate-500"}`}>
                  <div className="flex flex-col">
                    <span className="text-xs uppercase tracking-wider font-semibold opacity-70">Matches Found</span>
                    <span className="text-xl font-bold">{c.total_matches || 0} Hits</span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-xs uppercase tracking-wider font-semibold opacity-70">Videos Scanned</span>
                    <span className="text-xl font-bold text-slate-300">{c.videos_analyzed || 0} Logs</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New Case Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-2xl rounded-3xl overflow-hidden shadow-2xl relative border-emerald-500/30">
            
            <div className="flex justify-between items-center p-6 border-b border-white/10 bg-white/5">
              <h2 className="text-2xl font-bold text-white">Register Missing Child</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-8 space-y-6">
              {error && <div className="bg-red-500/20 text-red-300 px-4 py-3 rounded-lg border border-red-500/30 text-sm">{error}</div>}
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">FIR / Case Number <span className="text-red-500">*</span></label>
                  <input required name="case_number" value={formData.case_number} onChange={handleInputChange} type="text" className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500/50" placeholder="e.g. FIR-2024-001" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Child's Name <span className="text-red-500">*</span></label>
                  <input required name="child_name" value={formData.child_name} onChange={handleInputChange} type="text" className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500/50" placeholder="Full Name" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Age (Years) <span className="text-red-500">*</span></label>
                  <input required name="child_age" value={formData.child_age} onChange={handleInputChange} type="number" min="0" className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500/50" placeholder="e.g. 6" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Last Seen Date</label>
                  <input name="last_seen_date" value={formData.last_seen_date} onChange={handleInputChange} type="datetime-local" className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500/50" />
                </div>
              </div>
              
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Last Seen Location / Area</label>
                <input name="last_seen_place" value={formData.last_seen_place} onChange={handleInputChange} type="text" className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500/50" placeholder="e.g. Howrah Railway Station, Platform 5" />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Reference Photo (Frontal Face clearly visible) <span className="text-red-500">*</span></label>
                <div className="relative border-2 border-dashed border-slate-700 rounded-xl p-4 hover:border-emerald-500/50 transition-colors bg-slate-900">
                  <input required type="file" accept="image/*" onChange={handlePhotoChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                  <div className="flex items-center justify-center space-x-3 pointer-events-none">
                    <User className="w-6 h-6 text-emerald-500" />
                    <span className="text-slate-300 font-medium">{photo ? photo.name : "Click to select or drag and drop image"}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-1">This photo will be sent to the GPU cluster to extract a 512-dim embedding for recognition.</p>
              </div>

              <div className="flex justify-end pt-4 mt-8 border-t border-white/10">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-6 py-2 rounded-lg font-medium text-slate-400 hover:text-white mr-4 transition-colors">Cancel</button>
                <button type="submit" disabled={submitting} className="glass-button-primary px-8 py-2 rounded-lg font-medium shadow-lg flex items-center">
                  {submitting ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Processing AI Face...</> : 'Register Case'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
