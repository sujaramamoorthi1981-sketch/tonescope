import { History, LayoutDashboard, LogOut, Mic } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const link = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? "bg-signal text-ink" : "text-mist/80 hover:bg-white/10"
  }`;

export default function AppLayout() {
  const { user, signOut } = useAuth();
  return (
    <div className="flex h-screen flex-col md:flex-row">
      <aside className="flex items-center gap-2 bg-spruce p-3 md:w-56 md:flex-col md:items-stretch md:p-4">
        <div className="font-display text-xl font-bold text-mist md:mb-4">ToneScope</div>
        <nav className="flex flex-1 gap-1 md:flex-col" aria-label="Main">
          <NavLink to="/analyze" className={link}><Mic size={16} /> Analyze</NavLink>
          <NavLink to="/history" className={link}><History size={16} /> History</NavLink>
          <NavLink to="/dashboard" className={link}><LayoutDashboard size={16} /> Dashboard</NavLink>
        </nav>
        <div className="flex items-center gap-2 text-sm text-mist/70 md:flex-col md:items-stretch">
          <span className="hidden truncate md:block">{user?.name}</span>
          <button onClick={signOut} className="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-white/10" aria-label="Log out">
            <LogOut size={16} /> <span className="hidden md:inline">Log out</span>
          </button>
        </div>
      </aside>
      <main className="min-h-0 flex-1"><Outlet /></main>
    </div>
  );
}
