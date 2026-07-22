import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../lib/api';

type Step = 'email' | 'otp' | 'reset' | 'done';

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('email');

  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [devOtp, setDevOtp] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [resendTimer, setResendTimer] = useState(0);
  const [showPassword, setShowPassword] = useState(false);

  // Countdown timer for resend
  useEffect(() => {
    if (resendTimer <= 0) return;
    const t = setTimeout(() => setResendTimer(s => s - 1), 1000);
    return () => clearTimeout(t);
  }, [resendTimer]);

  const handleSendOtp = async () => {
    if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      setError('Please enter a valid email address');
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      const res = await authApi.forgotPassword(email);
      if (res.data.dev_otp) setDevOtp(res.data.dev_otp);
      setResendTimer(60);
      setStep('otp');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send OTP. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOtpChange = (idx: number, val: string) => {
    if (val.length > 1) return; // Only single digit
    const next = [...otp];
    next[idx] = val.replace(/\D/g, '');
    setOtp(next);
    // Auto-focus next
    if (val && idx < 5) {
      const nextInput = document.getElementById(`otp-${idx + 1}`);
      nextInput?.focus();
    }
  };

  const handleOtpKeyDown = (idx: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[idx] && idx > 0) {
      const prev = document.getElementById(`otp-${idx - 1}`);
      prev?.focus();
    }
  };

  const handleVerifyOtp = async () => {
    const otpStr = otp.join('');
    if (otpStr.length < 6) { setError('Please enter the complete 6-digit code'); return; }
    setIsLoading(true);
    setError('');
    try {
      const res = await authApi.verifyOtp(email, otpStr);
      setResetToken(res.data.reset_token);
      setStep('reset');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Incorrect OTP. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (newPassword.length < 8) { setError('Password must be at least 8 characters'); return; }
    if (newPassword !== confirmPassword) { setError('Passwords do not match'); return; }
    setIsLoading(true);
    setError('');
    try {
      await authApi.resetPassword(resetToken, newPassword);
      setStep('done');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-background" />
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="auth-logo">
              <svg viewBox="0 0 40 40" fill="none">
                <rect width="40" height="40" rx="10" fill="url(#logoGradFP)" />
                <path d="M20 8L8 14v12l12 6 12-6V14L20 8z" stroke="white" strokeWidth="2" fill="none" />
                <defs>
                  <linearGradient id="logoGradFP" x1="0" y1="0" x2="40" y2="40">
                    <stop offset="0%" stopColor="#FF6B35" /><stop offset="100%" stopColor="#FFC857" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            {step === 'email' && (<><h1 className="auth-title">Forgot Password</h1><p className="auth-subtitle">Enter your email to receive a reset code</p></>)}
            {step === 'otp' && (
              <>
                <h1 className="auth-title">Enter OTP</h1>
                {!devOtp && (
                  <p className="auth-subtitle">Code sent to {email} · expires in 10 minutes</p>
                )}
              </>
            )}
            {step === 'reset' && (<><h1 className="auth-title">New Password</h1><p className="auth-subtitle">Create a strong password</p></>)}
            {step === 'done' && (<><h1 className="auth-title">Password Reset!</h1><p className="auth-subtitle">You can now sign in with your new password</p></>)}
          </div>

          <div className="auth-form">
            {/* Step 1: Email */}
            {step === 'email' && (
              <>
                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <input
                    type="email"
                    className="form-input"
                    placeholder="you@example.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSendOtp()}
                    autoFocus
                  />
                </div>
                {error && <div className="form-error-banner">{error}</div>}
                {error && error.includes("No account found") ? (
                  <div className="flex flex-col gap-2 mt-2 w-full">
                    <button className="btn-primary btn-full" onClick={() => navigate('/register')}>
                      Create Account
                    </button>
                    <button className="btn-secondary btn-full" onClick={() => navigate('/login')}>
                      Back to Login
                    </button>
                  </div>
                ) : (
                  <button className={`btn-primary btn-full ${isLoading ? 'loading' : ''}`} onClick={handleSendOtp} disabled={isLoading}>
                    {isLoading ? 'Sending...' : 'Send Reset Code'}
                  </button>
                )}
              </>
            )}

            {/* Step 2: OTP */}
            {step === 'otp' && (
              <>
                {devOtp && (
                  <div className="dev-banner" style={{ background: 'rgba(255, 200, 87, 0.1)', border: '1px solid rgba(255, 200, 87, 0.2)', color: '#FFC857', padding: '12px', borderRadius: '8px', marginBottom: '16px', textAlign: 'center', fontSize: '13px' }}>
                    🛠 <strong>Developer Mode</strong> — Email delivery is disabled. OTP: <strong>{devOtp}</strong>
                  </div>
                )}
                <div className="otp-inputs">
                  {otp.map((digit, idx) => (
                    <input
                      key={idx}
                      id={`otp-${idx}`}
                      type="text"
                      inputMode="numeric"
                      className={`otp-input ${error ? 'error' : ''}`}
                      value={digit}
                      onChange={e => handleOtpChange(idx, e.target.value)}
                      onKeyDown={e => handleOtpKeyDown(idx, e)}
                      maxLength={1}
                      autoFocus={idx === 0}
                    />
                  ))}
                </div>
                {error && <div className="form-error-banner">{error}</div>}
                <button className={`btn-primary btn-full ${isLoading ? 'loading' : ''}`} onClick={handleVerifyOtp} disabled={isLoading}>
                  {isLoading ? 'Verifying...' : 'Verify Code'}
                </button>
                <div className="otp-resend">
                  {resendTimer > 0 ? (
                    <span className="otp-resend-timer">Resend in {resendTimer}s</span>
                  ) : (
                    <button className="btn-ghost btn-sm" onClick={handleSendOtp}>Resend OTP</button>
                  )}
                </div>
              </>
            )}

            {/* Step 3: New password */}
            {step === 'reset' && (
              <>
                <div className="form-group">
                  <label className="form-label">New Password</label>
                  <div className="form-input-wrap">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className="form-input"
                      placeholder="Minimum 8 characters"
                      value={newPassword}
                      onChange={e => setNewPassword(e.target.value)}
                      autoFocus
                    />
                    <button type="button" className="form-input-toggle" onClick={() => setShowPassword(s => !s)}>
                      {showPassword ? '🙈' : '👁'}
                    </button>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Confirm Password</label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="form-input"
                    placeholder="Repeat your password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                  />
                </div>
                {error && <div className="form-error-banner">{error}</div>}
                <button className={`btn-primary btn-full ${isLoading ? 'loading' : ''}`} onClick={handleResetPassword} disabled={isLoading}>
                  {isLoading ? 'Resetting...' : 'Reset Password'}
                </button>
              </>
            )}

            {/* Done */}
            {step === 'done' && (
              <div className="auth-success">
                <div className="auth-success-icon">✓</div>
                <p>Your password has been reset successfully.</p>
                <button className="btn-primary btn-full" onClick={() => navigate('/login')}>
                  Sign In
                </button>
              </div>
            )}
          </div>

          {step !== 'done' && (
            <div className="auth-footer">
              Remember your password? <Link to="/login" className="auth-link">Sign In</Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
