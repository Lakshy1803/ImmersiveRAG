"use client";

import React, { useEffect, useState } from "react";

const ThemeToggle: React.FC = () => {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    // Check local storage or system preference on mount
    const savedTheme = localStorage.getItem("theme");
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    if (savedTheme === "light") {
      setIsDark(false);
      document.documentElement.classList.remove("dark");
    } else if (savedTheme === "dark") {
      setIsDark(true);
      document.documentElement.classList.add("dark");
    } else if (systemPrefersDark) {
      setIsDark(true);
      document.documentElement.classList.add("dark");
    } else {
      // Default to dark as per "Corporate Luminary" aesthetic
      setIsDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggleTheme = () => {
    if (isDark) {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
      setIsDark(false);
    } else {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
      setIsDark(true);
    }
  };

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-2 px-4 py-2 rounded-full bg-surface-container-high border border-outline-variant/30 hover:border-primary/50 transition-all shadow-sm group"
      aria-label="Toggle Theme"
    >
      <span className="material-symbols-outlined text-sm text-on-surface/50 group-hover:text-primary transition-colors">
        {isDark ? "light_mode" : "dark_mode"}
      </span>
      <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface/50 group-hover:text-primary transition-colors">
        {isDark ? "Light Mode" : "Dark Mode"}
      </span>
    </button>
  );
};

export default ThemeToggle;
