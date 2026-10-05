import { useEffect, useState } from "react";
import type { Screen } from "../App";

interface Props {
  screen: Screen;
  setScreen: (s: Screen) => void;
  navItems: { id: Screen; label: string }[];
  isDark: boolean;
  setIsDark: (value: boolean) => void;
}

function CurrentDateTime() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  const date = now.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  });

  const time = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "Asia/Kolkata",
  });

  return (
    <span>
      {date} · {time} IST
    </span>
  );
}

export default function TopNav({
  screen,
  setScreen,
  navItems,
  isDark,
  setIsDark,
}: Props) {
  return (
    <header className="top-nav">
      <button
        className="brand"
        onClick={() => setScreen("live")}
        aria-label="StormSense home"
      >
        <span className="brand-mark" aria-hidden="true">
          S
        </span>

        <span>
          <strong>StormSense</strong>
          <small>
            Weather &amp; Disaster Monitoring
          </small>
        </span>
      </button>

      <nav
        className="primary-nav"
        aria-label="Main navigation"
      >
        {navItems.slice(0, 4).map((item) => (
          <button
            key={item.id}
            className={
              screen === item.id
                ? "nav-link active"
                : "nav-link"
            }
            onClick={() => setScreen(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="top-status">
        <span className="status-live">
          <span className="status-dot" />
          LIVE
        </span>

        <span className="status-divider" />

        <span className="current-time">
          <CurrentDateTime />
        </span>

        <span className="status-divider" />

        <span className="system-status-text">
          System operational
        </span>

        <button
          className="theme-toggle"
          onClick={() => setIsDark(!isDark)}
          aria-label={
            isDark
              ? "Switch to light mode"
              : "Switch to dark mode"
          }
        >
          <span aria-hidden="true">
            {isDark ? "☀" : "◐"}
          </span>

          <span>
            {isDark ? "Light" : "Dark"}
          </span>
        </button>

        <button
          className="help-button"
          onClick={() => setScreen("system")}
        >
          Help
        </button>
      </div>
    </header>
  );
}