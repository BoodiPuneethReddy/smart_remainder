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
            onClick={() => setShowProfileModal(true)}
            className="w-full text-left px-3 py-2 mb-1 rounded-input hover:bg-[var(--surface-hover)] transition-all cursor-pointer flex items-center justify-between"
          >
            <div className="truncate">
              <p className="text-body font-medium text-[var(--text-primary)] truncate">
                {user?.full_name ?? 'Punith'}
              </p>
              <p className="text-caption text-[var(--text-muted)] truncate">{user?.email ?? 'punithgodof@gmail.com'}</p>
              <p className="text-[10px] text-[var(--info,#3B82F6)] font-semibold truncate">{user?.college ?? 'SVCE'}</p>
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
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[var(--bg-secondary,#1E293B)] border border-[var(--card-border,#334155)] rounded-2xl p-6 w-full max-w-md shadow-2xl text-[var(--text-primary,#F8FAFC)]"
            >
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold flex items-center gap-2">👤 Account Profile</h3>
                <button onClick={() => setShowProfileModal(false)} className="text-slate-400 hover:text-white text-lg">✕</button>
              </div>
              <div className="space-y-4 text-sm">
                <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700">
                  <span className="text-xs text-slate-400 block mb-1">Full Name</span>
                  <p className="font-semibold text-base">{user?.full_name ?? 'Punith'}</p>
                </div>
                <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700">
                  <span className="text-xs text-slate-400 block mb-1">Email Address</span>
                  <p className="font-semibold text-base">{user?.email ?? 'punithgodof@gmail.com'}</p>
                </div>
                <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700">
                  <span className="text-xs text-slate-400 block mb-1">College / University</span>
                  <p className="font-semibold text-base text-blue-400">{user?.college ?? 'Sri Venkateswara College of Engineering'}</p>
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <button onClick={() => setShowProfileModal(false)} className="px-4 py-2 rounded-xl bg-slate-700 hover:bg-slate-600 font-medium">Close</button>
                <button onClick={handleLogout} className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 font-medium text-white">Sign Out</button>
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
