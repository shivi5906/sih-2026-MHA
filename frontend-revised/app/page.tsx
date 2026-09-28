'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { LoginScreen } from '@/components/login-screen';
import { CaseListView } from '@/components/case-list-view';
import { AppShell } from '@/components/app-shell';

export default function Home() {
  const { isAuthenticated } = useAuth();
  const [view, setView] = useState('list');
  useEffect(() => {
    const navigate = (event: Event) => setView((event as CustomEvent<string>).detail);
    window.addEventListener('vault-x:navigate', navigate);
    return () => window.removeEventListener('vault-x:navigate', navigate);
  }, []);

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return (
    <AppShell>
      <CaseListView initialView={view as 'list' | 'create' | 'detail' | 'evidence' | 'vasp' | 'audit' | 'report' | 'sahyog'} />
    </AppShell>
  );
}
