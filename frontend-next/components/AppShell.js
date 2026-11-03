"use client";
import Header from "./Header";
import SearchBar from "./SearchBar";
import Results from "./Results";
import Modal from "./Modal";
import Toast from "./Toast";

// Same top-level structure as the original <body>: header, main, #modal, #toast.
export default function AppShell() {
  return (
    <>
      <Header />
      <main>
        <SearchBar />
        <Results />
      </main>
      <Modal />
      <Toast />
    </>
  );
}
