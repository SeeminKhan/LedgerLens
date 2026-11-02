"use client";

import { useEffect, useState } from "react";

interface HealthStatus {
  status: string;
  service: string;
  version: string;
}

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const checkHealth = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/health`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data: HealthStatus = await response.json();
      setHealth(data);
    } catch (err: unknown) {
      setHealth(null);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to connect to backend");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 sm:p-12">
      <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white shadow-sm">
              LL
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              LedgerLens
            </h1>
          </div>
          <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
            AI-powered invoice extraction and GST validation.
          </p>
        </div>

        {/* Backend Status Card */}
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-800/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Backend Service Status
            </span>
            <button
              onClick={checkHealth}
              disabled={isLoading}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-700 disabled:opacity-50 dark:text-indigo-400 dark:hover:text-indigo-300"
            >
              {isLoading ? "Checking..." : "Re-check"}
            </button>
          </div>

          <div className="mt-4 flex items-center gap-3">
            {isLoading ? (
              <>
                <span className="relative flex h-3.5 w-3.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
                  <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-amber-500"></span>
                </span>
                <span className="text-sm font-medium text-amber-700 dark:text-amber-400">
                  Checking backend connection...
                </span>
              </>
            ) : health ? (
              <>
                <span className="relative flex h-3.5 w-3.5">
                  <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-emerald-500"></span>
                </span>
                <div className="text-sm">
                  <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                    Connected
                  </span>
                  <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">
                    ({health.service} v{health.version})
                  </span>
                </div>
              </>
            ) : (
              <>
                <span className="relative flex h-3.5 w-3.5">
                  <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-rose-500"></span>
                </span>
                <div className="text-sm">
                  <span className="font-semibold text-rose-700 dark:text-rose-400">
                    Disconnected
                  </span>
                  {error && (
                    <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">
                      ({error})
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="mt-4 border-t border-slate-200 pt-3 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
            Target Endpoint:{" "}
            <code className="rounded bg-slate-200 px-1.5 py-0.5 font-mono text-slate-800 dark:bg-slate-700 dark:text-slate-200">
              {apiUrl}/health
            </code>
          </div>
        </div>

        {/* Note / Guidance */}
        <div className="mt-6 text-xs text-slate-500 dark:text-slate-400">
          <p>
            Make sure the FastAPI backend is running locally on port 8000 using{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-slate-700 dark:bg-slate-800 dark:text-slate-300">
              uvicorn backend.main:app --reload --port 8000
            </code>
            .
          </p>
        </div>
      </div>
    </main>
  );
}
