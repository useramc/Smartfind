"use client";
import { usePathname } from "next/navigation";
import Header from "./Header";
import SearchBar from "./SearchBar";
import Results from "./Results";
import Modal from "./Modal";
import Toast from "./Toast";

// Same top-level structure as the original <body>: header, main, #modal, #toast.
// The admin route shows its dashboard in <main> instead of the search bar and results.
export default function AppShell({ children }) {
  const isAdmin = usePathname().startsWith("/admin");
  return (
    <>
      <Header />
      <main>
        {isAdmin ? null : (
          <>
            <SearchBar />
            <Results />
          </>
        )}
        {children}
      </main>
      <Modal />
      <Toast />
    </>
  );
}
