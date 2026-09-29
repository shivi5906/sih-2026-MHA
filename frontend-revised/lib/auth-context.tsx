'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Session, User } from './types';
import { api } from './api';

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
    try {
      const response = await api.login(email, password, role);
      
      const { token, user } = response as { token: string; user: User };
      
      setSession({
        user,
        token,
      });
      
      window.localStorage.setItem('vault-x-token', token);
      window.localStorage.setItem('vault-x-role', role); // keep for backward compatibility
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    setSession(null);
    window.localStorage.removeItem('vault-x-token');
    window.localStorage.removeItem('vault-x-role');
  };

  // Restore session on mount
  useEffect(() => {
    const token = typeof window !== 'undefined' ? window.localStorage.getItem('vault-x-token') : null;
    if (token) {
      api.me()
        .then((user) => {
          setSession({
            user: user as User,
            token
          });
        })
        .catch(() => {
          // Token invalid
          logout();
        });
    }
  }, []);

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
