'use client';

import { useAuth } from '@/lib/auth-context';
import { LoginScreen } from '@/components/login-screen';
import { CaseListView } from '@/components/case-list-view';
import { AppShell } from '@/components/app-shell';

export default function Home() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return (
    <AppShell>
      <CaseListView />
    </AppShell>
  );
}
