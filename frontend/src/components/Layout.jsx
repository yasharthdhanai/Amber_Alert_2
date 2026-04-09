import React from 'react';
import { NavLink } from 'react-router-dom';
import { Shield, LayoutDashboard, Settings, Video, Search, Bell } from 'lucide-react';
import { cn } from '../lib/utils';

export default function Layout({ children }) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-100">
      
      {/* Sidebar Navigation */}
      <aside className="w-64 flex-shrink-0 border-r border-white/10 glass-panel z-20 flex flex-col justify-between hidden md:flex">
        <div>
          <div className="h-20 flex items-center px-8 border-b border-white/10">
            <Shield className="w-8 h-8 text-emerald-400 mr-3 animate-pulse" />
            <h1 className="text-xl font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200">
              MCF System
            </h1>
          </div>
          
          <nav className="p-4 space-y-2 mt-4">
            <NavLink 
              to="/cases" 
              className={({ isActive }) => cn(
                "flex items-center px-4 py-3 rounded-lg font-medium transition-all duration-300 group",
                isActive 
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                  : "text-slate-400 hover:text-slate-100 hover:bg-white/5"
              )}
            >
              <LayoutDashboard className="w-5 h-5 mr-3 group-hover:scale-110 transition-transform" />
              Active Cases
            </NavLink>
            <NavLink 
              to="/live" 
              className={({ isActive }) => cn(
                "flex items-center px-4 py-3 rounded-lg font-medium transition-all duration-300 group",
                isActive 
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                  : "text-slate-400 hover:text-slate-100 hover:bg-white/5"
              )}
            >
              <Video className="w-5 h-5 mr-3 group-hover:scale-110 transition-transform" />
              Live Streams
            </NavLink>
          </nav>
        </div>
        
        <div className="p-4">
          <button className="flex items-center px-4 py-3 w-full rounded-lg font-medium text-slate-400 hover:text-slate-100 hover:bg-white/5 transition-all duration-300 group">
            <Settings className="w-5 h-5 mr-3 group-hover:rotate-90 transition-transform duration-500" />
            Settings
          </button>
        </div>
      </aside>

      {/* Main Container */}
      <main className="flex-1 flex flex-col h-screen relative z-10 overflow-hidden">
        
        {/* Top Header */}
        <header className="h-20 border-b border-white/10 glass-panel flex items-center justify-between px-8 z-20">
          <div className="flex items-center bg-black/20 rounded-full px-4 py-2 border border-white/5 w-96 backdrop-blur-md">
            <Search className="w-5 h-5 text-slate-400 mr-3" />
            <input 
              type="text" 
              placeholder="Search FIR number or child name..." 
              className="bg-transparent border-none outline-none text-sm w-full placeholder:text-slate-500"
            />
          </div>
          
          <div className="flex items-center space-x-6">
            <div className="relative cursor-pointer group">
              <Bell className="w-6 h-6 text-slate-300 group-hover:text-emerald-400 transition-colors" />
              <span className="absolute -top-1 -right-1 bg-red-500 w-3 h-3 rounded-full border-2 border-slate-950 animate-ping" />
              <span className="absolute -top-1 -right-1 bg-red-500 w-3 h-3 rounded-full border-2 border-slate-950" />
            </div>
            
            <div className="flex items-center space-x-3 pl-6 border-l border-white/10">
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-300 p-[2px]">
                <div className="w-full h-full rounded-full bg-slate-900 border-2 border-slate-900 flex items-center justify-center">
                  <span className="text-xs font-bold text-emerald-400">IO</span>
                </div>
              </div>
              <div className="hidden sm:block">
                <p className="text-sm font-semibold">Investigating Officer</p>
                <p className="text-xs text-slate-400">Station HQ</p>
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-8 relative">
          
          {/* Subtle animated background shapes for premium feel */}
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none -z-10" />
          <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-teal-600/10 rounded-full blur-[120px] pointer-events-none -z-10" />
          
          {children}
          
        </div>
      </main>
    </div>
  );
}
