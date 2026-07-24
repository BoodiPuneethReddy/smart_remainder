/**
 * components/layout/Sidebar.tsx — Application navigation sidebar.
 * Desktop: fixed left sidebar. Mobile: hamburger + bottom nav.
 */
import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, CheckSquare, Brain, BarChart2,
  LogOut, Menu, X, Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { authApi } from '@/lib/api';
import { iconSize } from '@/components/ui';

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/tasks',     icon: CheckSquare,     label: 'Tasks' },
  { to: '/planner',   icon: Brain,           label: 'AI Planner' },
  { to: '/analytics', icon: BarChart2,       label: 'Analytics' },
];

function NavItem({ to, icon: Icon, label }: typeof NAV_ITEMS[0]) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => cn(
        'flex items-center gap-3 px-3 py-2.5 rounded-input transition-all duration-150',
        'text-body font-medium group',
        isActive
          ? 'bg-[var(--surface-active)] text-[var(--text-primary)]'
          : 'text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]',
      )}
    >
      <Icon size={iconSize.button} className="flex-shrink-0 transition-transform group-hover:scale-105 duration-150" />
      <span>{label}</span>
    </NavLink>
  );
}

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [editName, setEditName] = useState(user?.full_name || '');
  const [editEmail, setEditEmail] = useState(user?.email || '');
  const [editCollege, setEditCollege] = useState(user?.college || user?.custom_college || '');
  const [editDepartment, setEditDepartment] = useState(user?.department || '');
  const [editYear, setEditYear] = useState(user?.year || '');
  const [editPreferences, setEditPreferences] = useState(user?.preferences || '');
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState('');

  const openProfile = () => {
    setEditName(user?.full_name || '');
    setEditEmail(user?.email || '');
    setEditCollege(user?.college || user?.custom_college || '');
    setEditDepartment(user?.department || '');
    setEditYear(user?.year || '');
    setEditPreferences(user?.preferences || '');
    setProfileMsg('');
    setShowProfileModal(true);
  };

  const handleSaveProfile = async () => {
    setSavingProfile(true);
    setProfileMsg('');
    try {
      const res = await authApi.updateProfile({
        full_name: editName,
        email: editEmail,
        custom_college: editCollege,
        department: editDepartment,
        year: editYear,
        preferences: editPreferences,
      });
      localStorage.setItem('user', JSON.stringify(res.data));
      setProfileMsg('Profile saved successfully!');
      setTimeout(() => {
        setShowProfileModal(false);
        window.location.reload();
      }, 1000);
    } catch (err: any) {
      setProfileMsg(err.response?.data?.detail || 'Failed to save profile');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <>
      {/* ── Desktop sidebar ─────────────────────────────────────────────── */}
      <aside className="hidden lg:flex flex-col w-56 flex-shrink-0 border-r border-[var(--card-border)] h-screen sticky top-0"
             style={{ background: 'var(--bg-secondary)' }}>
        {/* Logo */}
        <div className="p-6 border-b border-[var(--card-border)]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-badge flex items-center justify-center"
                 style={{ background: 'linear-gradient(135deg, var(--priority-high), var(--info))' }}>
              <Zap size={16} className="text-white" />
            </div>
            <div>
              <p className="text-h3 text-[var(--text-primary)] leading-tight">StudyAI</p>
              <p className="text-[10px] text-[var(--text-muted)]">AMD Hackathon</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {NAV_ITEMS.map((item) => <NavItem key={item.to} {...item} />)}
        </nav>

        {/* User profile section with interactive modal */}
        <div className="p-3 border-t border-[var(--card-border)]">
          <button
            onClick={openProfile}
            className="w-full text-left px-3 py-2 mb-1 rounded-input hover:bg-[var(--surface-hover)] transition-all cursor-pointer flex items-center justify-between"
          >
            <div className="truncate">
              <p className="text-body font-medium text-[var(--text-primary)] truncate">
                {user?.full_name || 'Account'}
              </p>
              <p className="text-caption text-[var(--text-muted)] truncate">{user?.email || ''}</p>
              {user?.college && <p className="text-[10px] text-[var(--info,#3B82F6)] font-semibold truncate">{user.college}</p>}
            </div>
            <span className="text-xs text-[var(--text-muted)]">⚙️</span>
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-input w-full text-body text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--danger)] transition-all duration-150"
          >
            <LogOut size={iconSize.button} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* ── Profile Details Modal ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {showProfileModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[var(--bg-secondary,#1E293B)] border border-[var(--card-border,#334155)] rounded-2xl p-6 w-full max-w-lg shadow-2xl text-[var(--text-primary,#F8FAFC)] space-y-4 my-8"
            >
              <div className="flex justify-between items-center pb-2 border-b border-slate-700">
                <h3 className="text-xl font-bold flex items-center gap-2">👤 Account Profile</h3>
                <button onClick={() => setShowProfileModal(false)} className="text-slate-400 hover:text-white text-lg">✕</button>
              </div>

              {profileMsg && (
                <div className={`p-3 rounded-xl text-sm font-medium ${profileMsg.includes('success') ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/20 text-red-300 border border-red-500/30'}`}>
                  {profileMsg}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Full Name</label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Email Address</label>
                  <input
                    type="email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">College / University</label>
                  <input
                    type="text"
                    value={editCollege}
                    onChange={(e) => setEditCollege(e.target.value)}
                    placeholder="Enter institution name"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Department</label>
                  <input
                    type="text"
                    value={editDepartment}
                    onChange={(e) => setEditDepartment(e.target.value)}
                    placeholder="Computer Science, ECE, etc."
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Year / Grade</label>
                  <input
                    type="text"
                    value={editYear}
                    onChange={(e) => setEditYear(e.target.value)}
                    placeholder="3rd Year, Semester 5"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Study Preferences</label>
                  <input
                    type="text"
                    value={editPreferences}
                    onChange={(e) => setEditPreferences(e.target.value)}
                    placeholder="e.g. Night study, 3h/day"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3 pt-3 border-t border-slate-700">
                <button onClick={() => setShowProfileModal(false)} className="px-4 py-2 rounded-xl bg-slate-700 hover:bg-slate-600 font-medium">Cancel</button>
                <button
                  onClick={handleSaveProfile}
                  disabled={savingProfile}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 font-medium text-white disabled:opacity-50"
                >
                  {savingProfile ? 'Saving...' : 'Save Profile'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── Mobile top bar ────────────────────────────────────────────────── */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-4 py-3 border-b border-[var(--card-border)]"
           style={{ background: 'var(--bg-secondary)' }}>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-badge flex items-center justify-center"
               style={{ background: 'linear-gradient(135deg, var(--priority-high), var(--info))' }}>
            <Zap size={14} className="text-white" />
          </div>
          <span className="text-h3 text-[var(--text-primary)]">StudyAI</span>
        </div>
        <button onClick={() => setMobileOpen(true)}
                className="p-2 rounded-input text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]">
          <Menu size={iconSize.button} />
        </button>
      </div>

      {/* ── Mobile drawer ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="lg:hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <motion.div
              initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="lg:hidden fixed left-0 top-0 bottom-0 z-50 w-64 flex flex-col border-r border-[var(--card-border)]"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div className="flex items-center justify-between p-4 border-b border-[var(--card-border)]">
                <span className="text-h3 text-[var(--text-primary)]">Menu</span>
                <button onClick={() => setMobileOpen(false)}
                        className="p-1.5 rounded-input text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]">
                  <X size={iconSize.button} />
                </button>
              </div>
              <nav className="flex-1 p-3 space-y-1">
                {NAV_ITEMS.map((item) => (
                  <div key={item.to} onClick={() => setMobileOpen(false)}>
                    <NavItem {...item} />
                  </div>
                ))}
              </nav>
              <div className="p-3 border-t border-[var(--card-border)]">
                <button onClick={handleLogout}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-input w-full text-body text-[var(--text-secondary)] hover:text-[var(--danger)] hover:bg-[var(--surface-hover)] transition-all">
                  <LogOut size={iconSize.button} /><span>Sign Out</span>
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
