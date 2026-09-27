'use client';

import React, { createContext, useContext, useState } from 'react';
import type { Session, User } from './types';

interface AuthContextType {
  session: Session | null;
  user: User | null;
  login: (email: string, password: string, role: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);

  const login = async (email: string, password: string, role: string) => {
    // Mock login - in production, call real auth API
    const mockUser: User = {
      id: `user-${Date.now()}`,
      name: email.split('@')[0],
      email,
      role: role as any,
      avatar: `https://avatar.example.com/${email}`,
    };

    const mockToken = btoa(`${email}:${Date.now()}`);

    setSession({
      user: mockUser,
      token: mockToken,
    });
  };

  const logout = () => {
    setSession(null);
  };

  return (
    <AuthContext.Provider
      value={{
        session,
        user: session?.user || null,
        login,
        logout,
        isAuthenticated: !!session,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
