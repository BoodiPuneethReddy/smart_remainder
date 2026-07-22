/**
 * pages/Login.tsx — Premium Redesigned Landing & Login Page.
 * Layout: Split screen (60% Interactive AI Hero / 40% Login Form) on desktop.
 * Backdrop: Floating particles, aurora gradient mesh, ambient rays, and floating semi-transparent text.
 */
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, Zap, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { Button, Input, Field } from '@/components/ui';
import { fadeSlideIn } from '@/lib/motion';
import { iconSize } from '@/components/ui';
import HeroVisualization from '@/components/HeroVisualization';

const FLOATING_WORDS = [
  { text: 'SMART STUDY REMINDER', top: '8%', scale: 1.2, duration: 45, delay: 0 },
  { text: 'AI', top: '22%', scale: 2.2, duration: 35, delay: 5 },
  { text: 'PLANNER', top: '38%', scale: 1.5, duration: 50, delay: 2 },
  { text: 'PRODUCTIVITY', top: '52%', scale: 1.1, duration: 40, delay: 8 },
  { text: 'STUDY COACH', top: '68%', scale: 1.3, duration: 48, delay: 4 },
  { text: 'AMD AI', top: '82%', scale: 1.8, duration: 38, delay: 10 },
  { text: 'AGENTIC AI', top: '15%', scale: 1.4, duration: 42, delay: 1 },
  { text: 'FOCUS', top: '32%', scale: 2.0, duration: 32, delay: 6 },
  { text: 'LEARN', top: '48%', scale: 1.6, duration: 46, delay: 3 },
  { text: 'ORGANIZE', top: '78%', scale: 1.2, duration: 55, delay: 7 },
];

// Generate simple static dust particles for background float
const DUST_PARTICLES = Array.from({ length: 25 }).map((_, i) => ({
  id: i,
  size: Math.random() * 3 + 1,
  top: `${Math.random() * 100}%`,
  left: `${Math.random() * 100}%`,
  duration: Math.random() * 15 + 10,
  delay: Math.random() * 5,
}));

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('punithgodof@gmail.com');
  const [password, setPassword] = useState('Punith@123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Subtle focus state to animate login card borders and icons
  const [isFocused, setIsFocused] = useState(false);
  const [isEmailFocused, setIsEmailFocused] = useState(false);
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch {
      setError('Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-screen flex flex-col md:flex-row bg-[var(--bg-primary)] overflow-hidden relative select-none">
      
      {/* ── BACKGROUND EFFECTS (Ambient / Particles / Blobs) ── */}
      
      {/* Dust Particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
        {DUST_PARTICLES.map((p) => (
          <motion.div
            key={p.id}
            animate={{
              y: [0, -50, 0],
              x: [0, 30, 0],
              opacity: [0.1, 0.4, 0.1],
            }}
            transition={{
              duration: p.duration,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: p.delay,
            }}
            style={{
              position: 'absolute',
              top: p.top,
              left: p.left,
              width: p.size,
              height: p.size,
              borderRadius: '50%',
              backgroundColor: '#FFF',
              filter: 'blur(0.5px)',
            }}
          />
        ))}
      </div>

      {/* Aurora Ambient Glowing Blobs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
        <motion.div
          animate={{
            scale: [1, 1.15, 0.9, 1],
            x: [0, 40, -30, 0],
            y: [0, -60, 40, 0],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
          style={{
            position: 'absolute',
            top: '10%',
            left: '5%',
            width: '40vw',
            height: '40vw',
            background: 'radial-gradient(circle, rgba(255,107,53,0.04) 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        <motion.div
          animate={{
            scale: [1, 1.2, 0.85, 1],
            x: [0, -50, 50, 0],
            y: [0, 80, -50, 0],
          }}
          transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
          style={{
            position: 'absolute',
            bottom: '5%',
            left: '30%',
            width: '45vw',
            height: '45vw',
            background: 'radial-gradient(circle, rgba(91,141,239,0.04) 0%, transparent 70%)',
            filter: 'blur(90px)',
          }}
        />
      </div>

      {/* Floating Typography (Only on Left 60% space on desktop) */}
      <div className="absolute left-0 top-0 w-full md:w-[50%] lg:w-[60%] h-full pointer-events-none overflow-hidden z-0 hidden md:block">
        {FLOATING_WORDS.map((w, i) => (
          <motion.div
            key={w.text}
            initial={{ x: '-20%', opacity: 0 }}
            animate={{
              x: '110%',
              opacity: [0, 0.03, 0.05, 0.03, 0],
            }}
            transition={{
              duration: w.duration,
              repeat: Infinity,
              ease: 'linear',
              delay: w.delay,
            }}
            style={{
              position: 'absolute',
              top: w.top,
              fontSize: `${18 * w.scale}px`,
              fontWeight: 800,
              color: 'var(--text-primary)',
              letterSpacing: '0.15em',
              whiteSpace: 'nowrap',
              filter: 'blur(3px)',
            }}
          >
            {w.text}
          </motion.div>
        ))}
      </div>

      {/* ── LEFT COLUMN: HERO AI VISUALIZATION (60%) ── */}
      <div className="hidden md:flex md:w-1/2 lg:w-[60%] border-r border-card-border h-full relative z-10 flex-col">
        <HeroVisualization />
      </div>

      {/* ── RIGHT COLUMN: PREMIUM GLASS LOGIN CARD (40%) ── */}
      <div className="w-full md:w-1/2 lg:w-[40%] flex items-center justify-center p-6 md:p-12 z-10 relative h-full min-h-screen">
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="w-full max-w-md"
        >
          {/* Card Border glow simulation */}
          <div className="relative group">
            <motion.div 
              animate={{
                opacity: isFocused ? 0.35 : 0.15,
              }}
              className="absolute -inset-0.5 rounded-[28px] bg-gradient-to-r from-[var(--priority-high)] to-[var(--info)] blur-md transition duration-500 pointer-events-none"
            />
            
            <form
              onSubmit={handleSubmit}
              className="relative glass rounded-[28px] p-10 shadow-[0_20px_50px_rgba(0,0,0,0.55)] backdrop-blur-[24px] space-y-6 flex flex-col justify-between"
              style={{ 
                background: 'rgba(11, 14, 20, 0.82)',
                borderColor: isFocused ? 'rgba(91, 141, 239, 0.35)' : 'rgba(255, 255, 255, 0.06)'
              }}
            >
              <div>
                <h1 className="text-display text-[var(--text-primary)] leading-tight tracking-tight">Welcome Back</h1>
                <p className="text-body-sm text-[var(--text-secondary)] mt-2 leading-relaxed">
                  Continue your academic journey with AI-powered planning and real-time smart constraints.
                </p>
              </div>

              {error && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-center gap-2.5 p-4 rounded-input text-body-sm text-[var(--danger)]"
                  style={{ background: 'rgba(255,107,53,0.08)', border: '1px solid rgba(255,107,53,0.15)' }}
                >
                  <AlertCircle size={iconSize.inline} className="flex-shrink-0" />
                  <span>{error}</span>
                </motion.div>
              )}

              <div className="space-y-4">
                <Field label="Email Address" htmlFor="email" required>
                  <Input
                    id="email" 
                    type="email" 
                    required 
                    autoComplete="email"
                    value={email} 
                    onChange={(e) => setEmail(e.target.value)}
                    onFocus={() => { setIsFocused(true); setIsEmailFocused(true); }}
                    onBlur={() => { setIsFocused(false); setIsEmailFocused(false); }}
                    leftIcon={
                      <Mail 
                        size={iconSize.inline} 
                        className={`transition-all duration-300 ${isEmailFocused ? 'text-[var(--info)] scale-110' : 'text-[var(--text-secondary)]'}`} 
                      />
                    }
                    placeholder="student@university.edu"
                    className="focus:shadow-[0_0_20px_rgba(91,141,239,0.25)] focus:border-[var(--info)] transition-all duration-300 h-11"
                  />
                </Field>

                <Field label="Password" htmlFor="password" required>
                  <Input
                    id="password" 
                    type="password" 
                    required 
                    autoComplete="current-password"
                    value={password} 
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => { setIsFocused(true); setIsPasswordFocused(true); }}
                    onBlur={() => { setIsFocused(false); setIsPasswordFocused(false); }}
                    leftIcon={
                      <Lock 
                        size={iconSize.inline} 
                        className={`transition-all duration-300 ${isPasswordFocused ? 'text-[var(--info)] scale-110' : 'text-[var(--text-secondary)]'}`} 
                      />
                    }
                    placeholder="••••••••••"
                    className="focus:shadow-[0_0_20px_rgba(91,141,239,0.25)] focus:border-[var(--info)] transition-all duration-300 h-11"
                  />
                </Field>
              </div>

              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full pt-2"
              >
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full h-12 rounded-input font-bold text-body text-white relative overflow-hidden group/btn flex items-center justify-center gap-2 transition-all duration-300 disabled:opacity-50"
                  style={{
                    background: 'linear-gradient(135deg, var(--priority-high) 0%, var(--info) 50%, var(--priority-high) 100%)',
                    backgroundSize: '200% auto',
                    boxShadow: '0 4px 20px rgba(91, 141, 239, 0.25)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundPosition = 'right center';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundPosition = 'left center';
                  }}
                >
                  {/* Premium Hover Shine Sweep Overlay */}
                  <motion.span
                    className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none"
                    initial={{ x: '-100%' }}
                    whileHover={{ x: '100%' }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                  />

                  <span>{loading ? 'Authenticating…' : 'Launch Study Assistant'}</span>
                  {!loading && <ArrowRight size={16} className="group-hover/btn:translate-x-1 transition-transform" />}
                </button>
              </motion.div>

              {/* Navigation Links */}
              <div className="pt-4 border-t border-card-border/40 flex flex-col items-center gap-2">
                <Link to="/forgot-password" className="text-caption text-[var(--priority-medium)] hover:text-white hover:underline transition-colors">
                  Forgot your password?
                </Link>
                <span className="text-caption text-[var(--text-secondary)]">
                  First time here?{' '}
                  <Link to="/register" className="text-[var(--priority-high)] hover:text-white font-semibold hover:underline transition-colors">
                    Create your account →
                  </Link>
                </span>
              </div>
            </form>
          </div>
        </motion.div>
      </div>

    </div>
  );
}

