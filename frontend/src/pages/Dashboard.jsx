import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, MapPin, User, Plus, FileVideo, Activity } from 'lucide-react';

const DUMMY_CASES = [
  {
    id: "MCF-2024-001",
    child_name: "Aarav Sharma",
    age: 6,
    last_seen_date: "2024-11-15T08:30:00Z",
    last_seen_place: "Howrah Railway Station, Platform 5",
    status: "active",
    matches: 3,
    videos: 12,
    image_url: "https://images.unsplash.com/photo-1543332143-4e8c27e3256f?w=400&q=80"
  },
  {
    id: "MCF-2024-002",
    child_name: "Priya Patel",
    age: 8,
    last_seen_date: "2024-11-16T14:15:00Z",
    last_seen_place: "VT Terminus, Mumbai",
    status: "active",
    matches: 0,
    videos: 5,
    image_url: "https://images.unsplash.com/photo-1514036783265-fba9577fc473?w=400&q=80"
  }
];

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Header Section */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold mb-2">Active Cases</h1>
          <p className="text-slate-400">Monitoring real-time CCTV feeds and processing manual uploads.</p>
        </div>
        
        <button className="flex items-center px-6 py-3 rounded-lg glass-button-primary">
          <Plus className="w-5 h-5 mr-2" />
          New Case
        </button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: "Active Monitors", value: "24", icon: Activity, color: "text-emerald-400" },
          { label: "Pending Uploads", value: "8", icon: FileVideo, color: "text-blue-400" },
          { label: "Confirmed Matches", value: "14", icon: User, color: "text-purple-400" },
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
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-8 pt-4">
        {DUMMY_CASES.map(c => (
          <div 
            key={c.id} 
            onClick={() => navigate(`/cases/${c.id}`)}
            className="group relative glass-panel rounded-2xl overflow-hidden cursor-pointer hover:shadow-2xl hover:shadow-emerald-500/10 transition-all duration-500 border border-white/5 hover:border-emerald-500/30"
          >
            {/* Image Header */}
            <div className="h-48 w-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-t from-slate-900 to-transparent z-10 opacity-90" />
              <img 
                src={c.image_url} 
                className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-700"
                alt={c.child_name} 
              />
              <div className="absolute bottom-4 left-5 z-20 flex justify-between items-end w-[calc(100%-40px)]">
                <div>
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 flex items-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
                      ACTIVE
                    </span>
                    <span className="text-xs text-slate-300 font-medium">{c.id}</span>
                  </div>
                  <h2 className="text-2xl font-bold text-white">{c.child_name}, <span className="opacity-75 text-lg">{c.age}</span></h2>
                </div>
              </div>
            </div>

            {/* Details Body */}
            <div className="p-5 space-y-4">
              <div className="space-y-2">
                <div className="flex items-center text-sm text-slate-400">
                  <Clock className="w-4 h-4 mr-3 text-slate-500" />
                  <span>Last seen <strong className="text-slate-200">14 hours ago</strong></span>
                </div>
                <div className="flex items-center text-sm text-slate-400">
                  <MapPin className="w-4 h-4 mr-3 text-slate-500" />
                  <span className="truncate">{c.last_seen_place}</span>
                </div>
              </div>

              {/* Match Indicator */}
              <div className={`mt-4 pt-4 border-t border-white/10 flex items-center justify-between ${c.matches > 0 ? "text-emerald-400" : "text-slate-500"}`}>
                <div className="flex flex-col">
                  <span className="text-xs uppercase tracking-wider font-semibold opacity-70">Matches Found</span>
                  <span className="text-xl font-bold">{c.matches} Hits</span>
                </div>
                <div className="flex flex-col text-right">
                  <span className="text-xs uppercase tracking-wider font-semibold opacity-70">Videos Scanned</span>
                  <span className="text-xl font-bold text-slate-300">{c.videos} Logs</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
