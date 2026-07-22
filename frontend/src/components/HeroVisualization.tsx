import React, { useState, useEffect, useRef, Suspense, lazy, Component, ErrorInfo, ReactNode } from 'react';
import { motion, AnimatePresence, useMotionValue, useSpring } from 'framer-motion';
import { 
  FileText, Cpu, Sliders, CheckSquare, Paperclip, BarChart2, Zap, Shield, GraduationCap, Bell, Calendar, ArrowRight, Activity
} from 'lucide-react';
const ThreeDScene = lazy(() => import('./ThreeDScene'));

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class CanvasErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false
  };

  public static getDerivedStateFromError(_: Error): ErrorBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Canvas error caught by boundary:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

function CSSFallbackCore() {
  return (
    <div className="relative w-full h-full flex items-center justify-center min-h-[380px]">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
        className="absolute w-72 h-72 rounded-full border border-dashed border-[var(--info)] opacity-20 pointer-events-none"
      />
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 35, repeat: Infinity, ease: 'linear' }}
        className="absolute w-80 h-80 rounded-full border border-dashed border-[var(--priority-high)] opacity-10 pointer-events-none"
      />
      <motion.div
        animate={{
          scale: [1, 1.15, 0.9, 1],
          borderRadius: [
            "42% 58% 70% 30% / 45% 45% 55% 55%",
            "70% 30% 52% 48% / 60% 40% 60% 40%",
            "42% 58% 70% 30% / 45% 45% 55% 55%"
          ]
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        className="w-48 h-48 bg-gradient-to-tr from-[var(--priority-high)] to-[var(--info)] blur-md opacity-80 shadow-[0_0_60px_rgba(255,107,53,0.25)] pointer-events-auto cursor-pointer"
      />
    </div>
  );
}

const METRICS = [
  { value: '38,376+', label: 'Indian Colleges', desc: 'Pre-seeded aliases directory' },
  { value: '3', label: 'Intelligent Agents', desc: 'Planner, Recommend, Reminder' },
  { value: '100%', label: 'Explainable Planning', desc: 'Zero schedule hallucinations' },
  { value: 'PDF + OCR', label: 'Academic Import', desc: 'Timetables & syllabus parser' },
];

const WORKFLOW_STEPS = [
  { label: 'Import Doc', desc: 'PDF / Image Entry', icon: <Paperclip size={14} /> },
  { label: 'AI Parse', desc: 'Document Analysis', icon: <Cpu size={14} /> },
  { label: 'Extract Meta', desc: 'Deadlines & Tasks', icon: <Sliders size={14} /> },
  { label: 'Score Priority', desc: 'Deterministic Engine', icon: <Shield size={14} /> },
  { label: 'Generate Schedule', desc: 'Dynamic Calendar', icon: <Calendar size={14} /> },
  { label: 'Smart Alerts', desc: 'Push & Analytics', icon: <Bell size={14} /> },
];

function AnimatedCounter({ value, duration = 1.2 }: { value: string; duration?: number }) {
  const numberValue = parseInt(value.replace(/[^0-9]/g, ''));
  const isPercent = value.includes('%');
  const isPlus = value.includes('+');
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (isNaN(numberValue)) return;
    let start = 0;
    const end = numberValue;
    const totalMiliseconds = duration * 1000;
    const incrementTime = Math.max(Math.floor(totalMiliseconds / end), 16);
    
    const timer = setInterval(() => {
      start += Math.ceil(end / (totalMiliseconds / incrementTime));
      if (start >= end) {
        clearInterval(timer);
        setCount(end);
      } else {
        setCount(start);
      }
    }, incrementTime);

    return () => clearInterval(timer);
  }, [numberValue, duration]);

  if (isNaN(numberValue)) {
    return <span>{value}</span>;
  }

  return (
    <span>
      {count.toLocaleString()}
      {isPercent ? '%' : ''}
      {isPlus ? '+' : ''}
    </span>
  );
}

export default function HeroVisualization() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeStep, setActiveStep] = useState(0);
  
  // Parallax spring values for mouse interaction
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 60, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 60, damping: 20 });

  // Loop through workflow steps every 3.2 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % WORKFLOW_STEPS.length);
    }, 3200);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) - rect.width / 2;
      const y = (e.clientY - rect.top) - rect.height / 2;
      mouseX.set((x / rect.width) * 20);
      mouseY.set((y / rect.height) * 20);
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY]);

  return (
    <div 
      ref={containerRef}
      className="w-full h-full flex flex-col justify-between p-8 relative overflow-hidden select-none bg-[rgba(11,14,20,0.45)]"
    >
      {/* Top Header & Brand */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="flex items-center justify-between z-20 w-full"
      >
        <div className="flex items-center gap-4">
          <motion.div 
            animate={{ rotate: 360 }}
            transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
            className="w-10 h-10 rounded-xl flex items-center justify-center border border-card-border"
            style={{ background: 'linear-gradient(135deg, rgba(255,107,53,0.15), rgba(91,141,239,0.15))' }}
          >
            <Zap size={20} className="text-[#FF6B35]" />
          </motion.div>
          <div>
            <h2 className="text-body font-bold text-[#F5F7FA] leading-none">Smart Study Reminder AI</h2>
            <span className="text-caption text-[#98A2B3] mt-1 block">Deterministic AI Study Coach • AMD Powered</span>
          </div>
        </div>

        {/* Live Active step badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-card-border bg-[#0B0E14]/85 backdrop-blur-md shadow-floating">
          <span className="w-2 h-2 rounded-full bg-[#FF6B35] animate-pulse" />
          <span className="text-[10px] font-extrabold uppercase tracking-widest text-[#F5F7FA]">
            Step {activeStep + 1}: {WORKFLOW_STEPS[activeStep].label}
          </span>
        </div>
      </motion.div>

      {/* Hero Typography */}
      <div className="mt-5 z-20 max-w-[640px] space-y-2">
        <h1 className="text-h1 font-extrabold text-[#F5F7FA] tracking-tight leading-tight">
          Plan Smarter. <span className="text-[#FF6B35]">Study Better.</span>
        </h1>
        <p className="text-caption text-[#C9D1D9] leading-relaxed font-normal">
          Smart Study Reminder AI converts course documents, timetables, and tasks into an explainable, deterministic study plan integrated with automated notifications.
        </p>
      </div>

      {/* Main Interactive Stage Area */}
      <div className="flex-1 flex items-center justify-center relative min-h-[340px] my-3">
        {/* 3D Crystal Core Layer */}
        <div className="absolute inset-0 z-0 flex items-center justify-center">
          <CanvasErrorBoundary fallback={<CSSFallbackCore />}>
            <Suspense fallback={<CSSFallbackCore />}>
              <ThreeDScene activeStep={activeStep} />
            </Suspense>
          </CanvasErrorBoundary>
        </div>

        {/* ── WORKFLOW STORYBOARD STAGE OVERLAYS (Conditional Animations) ── */}
        <div className="absolute inset-0 z-10 w-full h-full pointer-events-none flex items-center justify-center">
          <AnimatePresence mode="wait">
            
            {/* Step 0: Document Import Entry */}
            {activeStep === 0 && (
              <motion.div
                key="step-import"
                initial={{ opacity: 0, x: -120, scale: 0.8 }}
                animate={{ opacity: 1, x: -30, scale: 1 }}
                exit={{ opacity: 0, x: 20, scale: 0.8, filter: 'blur(5px)' }}
                transition={{ type: 'spring', stiffness: 100, damping: 15 }}
                className="absolute left-[10%] flex flex-col items-center gap-3 p-5 rounded-2xl border border-[rgba(91,141,239,0.4)] bg-[#0B0E14]/95 backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] pointer-events-auto w-52"
              >
                <div className="relative w-12 h-12 rounded-xl bg-[rgba(91,141,239,0.15)] flex items-center justify-center border border-[rgba(91,141,239,0.3)] text-[#5B8DEF]">
                  <FileText size={24} />
                  {/* Glowing Laser Scan Bar */}
                  <motion.div 
                    animate={{ y: [0, 36, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                    className="absolute left-0 right-0 top-1 h-[2px] bg-gradient-to-r from-transparent via-[#2EC4B6] to-transparent shadow-[0_0_8px_#2EC4B6]"
                  />
                </div>
                <div className="text-center">
                  <div className="text-caption font-bold text-[#F5F7FA]">Timetable.pdf</div>
                  <div className="text-[10px] text-[#C9D1D9] mt-1">Extracting tasks & dates...</div>
                </div>
              </motion.div>
            )}

            {/* Step 1: AI OCR / Parsing Analysis */}
            {activeStep === 1 && (
              <motion.div
                key="step-analyze"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="absolute flex flex-col items-center gap-2 p-4 rounded-xl border border-[rgba(255,200,87,0.4)] bg-[#0B0E14]/95 backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] text-center w-52 pointer-events-auto"
              >
                <Activity size={18} className="text-[#FFC857] animate-pulse" />
                <div className="text-[11px] font-bold text-[#F5F7FA] uppercase tracking-wider">AI OCR Analyzer</div>
                <div className="w-full bg-card-border/40 h-1.5 rounded-full overflow-hidden mt-1">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 3 }}
                    className="h-full bg-gradient-to-r from-[#FFC857] to-[#FF6B35]"
                  />
                </div>
                <div className="text-[9px] text-[#C9D1D9] mt-1">Scanning text confidence: 98.4%</div>
              </motion.div>
            )}

            {/* Step 2: Information Extraction */}
            {activeStep === 2 && (
              <motion.div
                key="step-extract"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute w-full h-full flex flex-col items-center justify-between p-6 pointer-events-none"
              >
                {/* Float out metadata pills */}
                <motion.div
                  initial={{ opacity: 0, y: 30, x: -80 }}
                  animate={{ opacity: 1, y: 0, x: -50 }}
                  transition={{ delay: 0.1 }}
                  className="absolute left-[15%] top-[25%] px-3.5 py-2 rounded-full border border-[rgba(46,196,182,0.4)] bg-[#0B0E14]/95 backdrop-blur-md text-[10px] font-bold text-[#F5F7FA] shadow-[0_10px_30px_rgba(0,0,0,0.4)] flex items-center gap-1.5"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-[#2EC4B6]" />
                  Task: Algebra Exam Prep
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: -20, x: 80 }}
                  animate={{ opacity: 1, y: 0, x: 50 }}
                  transition={{ delay: 0.3 }}
                  className="absolute right-[15%] top-[30%] px-3.5 py-2 rounded-full border border-[rgba(46,196,182,0.4)] bg-[#0B0E14]/95 backdrop-blur-md text-[10px] font-bold text-[#F5F7FA] shadow-[0_10px_30px_rgba(0,0,0,0.4)] flex items-center gap-1.5"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-[#2EC4B6]" />
                  Due: Oct 24, 2026
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 40, x: 60 }}
                  animate={{ opacity: 1, y: 0, x: 30 }}
                  transition={{ delay: 0.5 }}
                  className="absolute right-[22%] bottom-[25%] px-3.5 py-2 rounded-full border border-[rgba(46,196,182,0.4)] bg-[#0B0E14]/95 backdrop-blur-md text-[10px] font-bold text-[#F5F7FA] shadow-[0_10px_30px_rgba(0,0,0,0.4)] flex items-center gap-1.5"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-[#2EC4B6]" />
                  Weight: 20% of Grade
                </motion.div>
              </motion.div>
            )}

            {/* Step 3: Priority Scoring */}
            {activeStep === 3 && (
              <motion.div
                key="step-score"
                initial={{ opacity: 0, scale: 0.8, y: 40 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8, y: -20 }}
                transition={{ type: 'spring', stiffness: 100, damping: 15 }}
                className="absolute right-[10%] flex flex-col items-center gap-2 p-5 rounded-2xl border border-[rgba(255,107,53,0.4)] bg-[#0B0E14]/95 backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] pointer-events-auto w-56 text-center"
              >
                <div className="text-caption font-bold text-[#98A2B3] uppercase tracking-wider">Priority Computed</div>
                <motion.div 
                  animate={{ scale: [1, 1.08, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  className="text-h1 font-extrabold text-[#FF6B35] leading-none my-1"
                >
                  92 <span className="text-body font-semibold text-[#98A2B3]">/100</span>
                </motion.div>
                <div className="text-[9px] text-[#C9D1D9] font-mono leading-normal">
                  Calculated based on workload, deadlines & academic weighting.
                </div>
              </motion.div>
            )}

            {/* Step 4: Schedule Allocation */}
            {activeStep === 4 && (
              <motion.div
                key="step-schedule"
                initial={{ opacity: 0, x: 120 }}
                animate={{ opacity: 1, x: 40 }}
                exit={{ opacity: 0, x: -20, filter: 'blur(5px)' }}
                transition={{ type: 'spring', stiffness: 100, damping: 15 }}
                className="absolute right-[10%] flex flex-col gap-2 p-4 rounded-xl border border-[rgba(91,141,239,0.4)] bg-[#0B0E14]/95 backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] pointer-events-auto w-60"
              >
                <div className="text-[10px] font-extrabold uppercase tracking-widest text-[#5B8DEF]">Study Plan Allocated</div>
                <div className="space-y-1.5 mt-1">
                  <div className="p-2 rounded bg-card/60 border border-card-border/60 text-[10px] font-bold text-[#F5F7FA] flex justify-between items-center">
                    <span>Algebra Session</span>
                    <span className="text-[9px] text-[#C9D1D9]">2:00 PM (90m)</span>
                  </div>
                  <div className="p-2 rounded bg-card/60 border border-card-border/60 text-[10px] font-bold text-[#F5F7FA] flex justify-between items-center opacity-80">
                    <span>Physics Homework</span>
                    <span className="text-[9px] text-[#C9D1D9]">4:30 PM (60m)</span>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Step 5: Alerts & Reminders */}
            {activeStep === 5 && (
              <motion.div
                key="step-remind"
                initial={{ opacity: 0, scale: 0.8, y: -40 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="absolute flex flex-col items-center gap-3 p-5 rounded-2xl border border-[rgba(46,196,182,0.4)] bg-[#0B0E14]/95 backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] pointer-events-auto w-52 text-center"
              >
                <motion.div
                  animate={{ rotate: [0, -10, 10, -10, 10, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                  className="w-12 h-12 rounded-full bg-[rgba(46,196,182,0.15)] flex items-center justify-center text-[#2EC4B6] border border-[rgba(46,196,182,0.3)]"
                >
                  <Bell size={22} />
                </motion.div>
                <div>
                  <div className="text-caption font-bold text-[#F5F7FA]">Reminders Scheduled</div>
                  <div className="text-[9px] text-[#C9D1D9] mt-1 leading-normal">Telegram / Gmail notifications dispatching soon.</div>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>

      {/* ── FLOW PROGRESS TIMELINE DOTS TRACKER (Horizontal connecting bar) ── */}
      <div className="z-20 w-full bg-[#0B0E14]/75 rounded-2xl border border-card-border p-4 backdrop-blur-md shadow-floating relative my-2">
        <div className="relative flex items-center justify-between w-full">
          {/* Base Connection line */}
          <div className="absolute left-[3%] right-[3%] h-[1px] bg-card-border/60 z-0 top-[18px]" />
          
          {/* Active progress line */}
          <motion.div 
            className="absolute left-[3%] h-[1px] bg-gradient-to-r from-[var(--info)] via-[#FF6B35] to-[#2EC4B6] z-0 top-[18px]"
            animate={{
              width: `${(activeStep / (WORKFLOW_STEPS.length - 1)) * 94}%`
            }}
            transition={{ duration: 0.8, ease: 'easeInOut' }}
          />

          {WORKFLOW_STEPS.map((step, index) => {
            const isActive = index === activeStep;
            const isCompleted = index < activeStep;

            return (
              <div 
                key={step.label} 
                onClick={() => setActiveStep(index)}
                className="flex flex-col items-center z-10 cursor-pointer group w-[15%]"
              >
                {/* Node bubble */}
                <motion.div
                  animate={{
                    borderColor: isActive ? '#FF6B35' : isCompleted ? '#2EC4B6' : 'rgba(255,255,255,0.15)',
                    scale: isActive ? 1.15 : 1,
                    backgroundColor: isActive ? 'var(--bg-secondary)' : isCompleted ? 'rgba(46,196,182,0.15)' : 'rgba(18,20,28,0.95)'
                  }}
                  transition={{ duration: 0.3 }}
                  className={`w-9 h-9 rounded-full border flex items-center justify-center shadow-floating transition-all duration-300 ${
                    isActive ? 'text-[#FF6B35] shadow-[0_0_15px_rgba(255,107,53,0.3)]' :
                    isCompleted ? 'text-[#2EC4B6]' : 'text-[#98A2B3] group-hover:text-[#F5F7FA] group-hover:border-card-border'
                  }`}
                >
                  {step.icon}
                </motion.div>
                
                {/* Step labels */}
                <span className={`text-[10px] font-bold text-center mt-2 tracking-wide transition-colors duration-300 ${
                  isActive ? 'text-[#F5F7FA] font-extrabold' : 'text-[#98A2B3]'
                }`}>
                  {step.label}
                </span>
                <span className="text-[8px] text-[#98A2B3] opacity-80 text-center leading-none mt-0.5 hidden lg:block">
                  {step.desc}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Floating statistics/metric cards at the bottom */}
      <div className="z-20 grid grid-cols-2 md:grid-cols-4 gap-4 mt-2">
        {METRICS.map((metric, i) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 + i * 0.1, ease: 'easeOut' }}
            whileHover={{ y: -5, borderColor: 'rgba(255,107,53,0.45)', boxShadow: '0 12px 30px rgba(0,0,0,0.45)' }}
            className="p-4 rounded-xl border border-card-border/80 bg-[#0B0E14]/85 backdrop-blur-[20px] transition-all duration-300 select-none shadow-[0_15px_35px_rgba(0,0,0,0.45)] flex flex-col justify-between"
          >
            <div>
              <span className="text-body-sm font-extrabold text-[#FF6B35] block">
                <AnimatedCounter value={metric.value} />
              </span>
              <span className="text-caption font-semibold text-[#F5F7FA] block mt-1">{metric.label}</span>
            </div>
            <p className="text-[10px] text-[#C9D1D9] mt-2 font-normal leading-normal">{metric.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

