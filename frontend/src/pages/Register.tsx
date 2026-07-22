import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi, College } from '../lib/api';
import CollegeSearch from '../components/ui/CollegeSearch';

type Step = 'details' | 'college';

export default function Register() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('details');

  // Form fields
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [dob, setDob] = useState('');
  const [college, setCollege] = useState<College | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showPassword, setShowPassword] = useState(false);

  const validateStep1 = () => {
    const errs: Record<string, string> = {};
    if (!fullName.trim()) errs.fullName = 'Full name is required';
    if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) errs.email = 'Valid email required';
    if (password.length < 8) errs.password = 'Minimum 8 characters';
    if (password !== confirmPassword) errs.confirmPassword = 'Passwords do not match';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleNext = () => {
    if (validateStep1()) setStep('college');
  };

  const handleRegister = async () => {
    const errs: Record<string, string> = {};
    if (!college) errs.college = 'Please select your college from the directory';
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setIsLoading(true);
    try {
      const res = await authApi.register({
        email,
        full_name: fullName,
        password,
        college_id: college!.id,
        date_of_birth: dob || undefined,
      });
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('user', JSON.stringify(res.data.user));
      navigate('/dashboard');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Registration failed. Please try again.';
      setErrors({ submit: msg });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-background" />
      <div className="auth-container">
        <div className="auth-card">
          {/* Header */}
          <div className="auth-header">
            <div className="auth-logo">
              <svg viewBox="0 0 40 40" fill="none">
                <rect width="40" height="40" rx="10" fill="url(#logoGrad)" />
                <path d="M20 8L8 14v12l12 6 12-6V14L20 8z" stroke="white" strokeWidth="2" fill="none" />
                <defs>
                  <linearGradient id="logoGrad" x1="0" y1="0" x2="40" y2="40">
                    <stop offset="0%" stopColor="#FF6B35" />
                    <stop offset="100%" stopColor="#FFC857" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <h1 className="auth-title">Create Account</h1>
            <p className="auth-subtitle">
              {step === 'details' ? 'Step 1 of 2 — Your details' : 'Step 2 of 2 — Your college'}
            </p>

            {/* Step indicators */}
            <div className="auth-steps">
              <div className={`auth-step ${step === 'details' ? 'active' : 'done'}`}>
                <div className="auth-step-dot">{step === 'college' ? '✓' : '1'}</div>
                <span>Details</span>
              </div>
              <div className="auth-step-line" />
              <div className={`auth-step ${step === 'college' ? 'active' : ''}`}>
                <div className="auth-step-dot">2</div>
                <span>College</span>
              </div>
            </div>
          </div>

          {/* Step 1 — Personal details */}
          {step === 'details' && (
            <div className="auth-form">
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className={`form-input ${errors.fullName ? 'error' : ''}`}
                  placeholder="Alex Morgan"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  autoFocus
                />
                {errors.fullName && <p className="form-error">{errors.fullName}</p>}
              </div>

              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  className={`form-input ${errors.email ? 'error' : ''}`}
                  placeholder="you@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                />
                {errors.email && <p className="form-error">{errors.email}</p>}
              </div>

              <div className="form-group">
                <label className="form-label">Date of Birth <span className="form-optional">(optional)</span></label>
                <input
                  type="date"
                  className="form-input"
                  value={dob}
                  onChange={e => setDob(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <div className="form-input-wrap">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className={`form-input ${errors.password ? 'error' : ''}`}
                    placeholder="Minimum 8 characters"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className="form-input-toggle"
                    onClick={() => setShowPassword(s => !s)}
                  >
                    {showPassword ? '🙈' : '👁'}
                  </button>
                </div>
                {errors.password && <p className="form-error">{errors.password}</p>}
              </div>

              <div className="form-group">
                <label className="form-label">Confirm Password</label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  className={`form-input ${errors.confirmPassword ? 'error' : ''}`}
                  placeholder="Repeat your password"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                />
                {errors.confirmPassword && <p className="form-error">{errors.confirmPassword}</p>}
              </div>

              <button
                type="button"
                className="btn-primary btn-full"
                onClick={handleNext}
              >
                Continue →
              </button>
            </div>
          )}

          {/* Step 2 — College selection */}
          {step === 'college' && (
            <div className="auth-form">
              <div className="form-group">
                <label className="form-label">Your College or University</label>
                <p className="form-hint">
                  Search from our directory of 38,000+ recognized Indian institutions.
                  Select from the dropdown — no free-text entries.
                </p>
                <CollegeSearch
                  value={college}
                  onChange={setCollege}
                  error={errors.college}
                />
              </div>

              {errors.submit && (
                <div className="form-error-banner">{errors.submit}</div>
              )}

              <div className="auth-form-actions">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setStep('details')}
                  disabled={isLoading}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  className={`btn-primary ${isLoading ? 'loading' : ''}`}
                  onClick={handleRegister}
                  disabled={isLoading}
                >
                  {isLoading ? 'Creating account...' : 'Create Account'}
                </button>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="auth-footer">
            Already have an account?{' '}
            <Link to="/login" className="auth-link">Sign In</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
