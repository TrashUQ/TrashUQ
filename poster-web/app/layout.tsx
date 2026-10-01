import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TrashUQ | Federated learning for intelligent waste monitoring',
  description: 'Meet the four engineers behind TrashUQ. Connect with the team and explore our paper and open-source federated learning project.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
