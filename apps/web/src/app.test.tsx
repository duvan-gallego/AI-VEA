import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the application title and backend status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              environment: "test",
              service: "ai-vea-api",
              status: "ok",
              version: "0.1.0",
            }),
        }),
      ),
    );

    render(<App />);

    expect(screen.getByRole("heading", { name: "AI VEA" })).toBeInTheDocument();
    expect(await screen.findByText("ai-vea-api is ok in test.")).toBeInTheDocument();
  });
});
