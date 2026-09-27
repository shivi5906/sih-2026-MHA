'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import type { UserRole } from '@/lib/types';

const roles: { value: UserRole; label: string }[] = [
  { value: 'Analyst', label: 'Analyst' },
  { value: 'Senior Investigator', label: 'Senior Investigator' },
  { value: 'Supervisor', label: 'Supervisor' },
  { value: 'Auditor', label: 'Auditor' },
];

export function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('analyst@vault.local');
  const [password, setPassword] = useState('••••••••');
  const [selectedRole, setSelectedRole] = useState<UserRole>('Analyst');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(email, password, selectedRole);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col items-center justify-center p-4">
      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-900/50 to-transparent"></div>

      <div className="w-full max-w-sm space-y-8">
        {/* Logo / Header */}
        <div className="space-y-2 text-center">
          <div className="inline-flex items-center gap-2 text-lg font-bold tracking-tight">
            <div className="w-8 h-8 border border-cyan-700/50 flex items-center justify-center rounded-sm">
              <span className="text-xs font-mono text-cyan-700">V</span>
            </div>
            <span>VAULT-X</span>
          </div>
          <p className="text-xs text-slate-500 font-mono">Law Enforcement Intelligence Platform</p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-5">
          {/* Email */}
          <div className="space-y-2">
            <label htmlFor="email" className="block text-xs font-mono text-slate-400 uppercase tracking-wider">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700/50 text-sm font-mono text-slate-50 focus:outline-none focus:border-cyan-700/70 transition-colors"
            />
          </div>

          {/* Password */}
          <div className="space-y-2">
            <label htmlFor="password" className="block text-xs font-mono text-slate-400 uppercase tracking-wider">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700/50 text-sm font-mono text-slate-50 focus:outline-none focus:border-cyan-700/70 transition-colors"
            />
          </div>

          {/* Role Selection */}
          <div className="space-y-2">
            <label className="block text-xs font-mono text-slate-400 uppercase tracking-wider">Role</label>
            <div className="grid grid-cols-2 gap-2">
              {roles.map((role) => (
                <button
                  key={role.value}
                  type="button"
                  onClick={() => setSelectedRole(role.value)}
                  className={`px-3 py-2 text-xs font-mono border transition-colors ${
                    selectedRole === role.value
                      ? 'border-cyan-700/80 bg-slate-800/50 text-slate-50'
                      : 'border-slate-700/50 bg-slate-900 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  {role.label}
                </button>
              ))}
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-6 px-4 py-2 bg-slate-700/40 border border-slate-600/60 text-sm font-mono text-slate-50 hover:bg-slate-700/60 hover:border-cyan-700/40 disabled:opacity-50 transition-all duration-150"
          >
            {isLoading ? 'AUTHENTICATING...' : 'AUTHENTICATE'}
          </button>
        </form>

        {/* Footer info */}
        <div className="text-center text-xs text-slate-600 font-mono space-y-1">
          <p>Demo Credentials</p>
          <p className="text-slate-700">Use any role to proceed</p>
        </div>
      </div>

      {/* Bottom accent line */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-900/30 to-transparent"></div>
    </div>
  );
}
