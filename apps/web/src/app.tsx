import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "./api";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: HealthResponse }
  | { status: "error"; message: string };

export function App() {
  const [health, setHealth] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    void getHealth(controller.signal)
      .then((data) => {
        setHealth({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setHealth({
          status: "error",
          message: error instanceof Error ? error.message : "Unexpected API error",
        });
      });

    return () => {
      controller.abort();
    };
  }, []);

  return (
    <main className="shell">
      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">React + TypeScript + FastAPI</p>
        <h1 id="page-title">AI VEA</h1>
        <p className="lede">
          A clean monorepo foundation with strict typing, linting, formatting, tests, and a backend
          health endpoint ready for real product work.
        </p>
      </section>

      <section className="status-panel" aria-live="polite">
        <span className={`status-dot status-dot--${health.status}`} />
        <div>
          <h2>Backend status</h2>
          {health.status === "loading" ? <p>Checking API health...</p> : null}
          {health.status === "error" ? <p>{health.message}</p> : null}
          {health.status === "ready" ? (
            <p>
              {health.data.service} is {health.data.status} in {health.data.environment}.
            </p>
          ) : null}
        </div>
      </section>
    </main>
  );
}
