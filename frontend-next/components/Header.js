"use client";
import { usePathname, useRouter } from "next/navigation";
import { useApp } from "./AppContext";

export default function Header() {
  const { ready, user, home, showSaved, showRecs, showHistory, authForm, logout, isLoggedIn } = useApp();
  const router = useRouter();
  const pathname = usePathname();

  // Logged in: go to the view's route (the page runs the action). Logged out or already
  // there: run the action directly, exactly like the original buttons.
  const go = (path, action) => (isLoggedIn() && pathname !== path ? router.push(path) : action());

  return (
    <header>
      <h1 onClick={home}>🔎 SmartFind</h1>
      <nav>
        <button className="sm" onClick={() => go("/saved", showSaved)}>♥ Saved</button>
        <button className="sm" onClick={() => go("/for-you", showRecs)}>✨ For you</button>
        <button className="sm" onClick={() => go("/history", showHistory)}>🕘 History</button>
        <span id="auth">
          {ready &&
            (user ? (
              <>
                <span className="mut">Hi, {user.name}</span>{" "}
                <button className="sm" onClick={() => logout()}>Logout</button>
              </>
            ) : (
              <button className="sm p" onClick={authForm}>Login / Register</button>
            ))}
        </span>
      </nav>
    </header>
  );
}
