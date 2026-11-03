import "./globals.css";
import { AppProvider } from "@/components/AppContext";
import AppShell from "@/components/AppShell";

export const metadata = { title: "SmartFind – AI Product Discovery" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          <AppShell />
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
