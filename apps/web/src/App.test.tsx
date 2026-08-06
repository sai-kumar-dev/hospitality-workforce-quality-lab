import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import {
  candidate,
  frontDeskJob,
  jsonResponse,
  pageOf,
  unauthorizedResponse,
} from "./test/fixtures";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ShiftBridge application", () => {
  it("introduces the marketplace with a clear primary journey", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(unauthorizedResponse()),
    );
    renderAt("/");

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "ShiftBridge Quality Engineering Lab",
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Explore open roles" }),
    ).toHaveAttribute("href", "/jobs");
    expect(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).toBeVisible();
    expect(await screen.findByRole("link", { name: "Sign in" })).toBeVisible();
  });

  it("associates required login validation with its fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(unauthorizedResponse()),
    );
    const user = userEvent.setup();
    renderAt("/login");

    await user.click(await screen.findByRole("button", { name: "Sign in" }));

    expect(screen.getByLabelText("Email address")).toHaveAccessibleErrorMessage(
      "Enter your email address.",
    );
    expect(screen.getByLabelText("Password")).toHaveAccessibleErrorMessage(
      "Enter your password.",
    );
  });

  it("presents invalid credentials as an accessible authentication failure", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (String(input).endsWith("/auth/me")) return unauthorizedResponse();
      return jsonResponse(
        {
          code: "INVALID_CREDENTIALS",
          title: "Authentication failed",
          status: 401,
          detail: "Email or password is incorrect.",
          request_id: "login-failed-request",
        },
        401,
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderAt("/login");

    await user.type(
      await screen.findByLabelText("Email address"),
      "wrong@example.test",
    );
    await user.type(screen.getByLabelText("Password"), "incorrect-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Sign in failed",
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Email or password is incorrect.",
    );
  });

  it("prevents registration when confirmation does not match", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(unauthorizedResponse()),
    );
    const user = userEvent.setup();
    renderAt("/register");

    await user.type(await screen.findByLabelText("Full name"), "Jordan Cook");
    await user.type(
      screen.getByLabelText("Email address"),
      "jordan@example.test",
    );
    await user.type(screen.getByLabelText("Password"), "strong-password");
    await user.type(
      screen.getByLabelText("Confirm password"),
      "different-password",
    );
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(
      screen.getByLabelText("Confirm password"),
    ).toHaveAccessibleErrorMessage("Passwords do not match.");
  });

  it("loads job results and exposes a semantic job-detail link", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) return unauthorizedResponse();
      if (url.includes("/jobs")) return jsonResponse(pageOf([frontDeskJob]));
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderAt("/jobs");

    expect(
      await screen.findByRole("heading", { name: "Front Desk Supervisor" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", {
        name: "View Front Desk Supervisor at Harbour House Hotel",
      }),
    ).toHaveAttribute("href", "/jobs/101");
    expect(screen.getByText("1 role found")).toBeVisible();
  });

  it("shows a retryable safe error when job search cannot reach the API", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (String(input).endsWith("/auth/me")) return unauthorizedResponse();
      throw new TypeError("connection refused with internal details");
    });
    vi.stubGlobal("fetch", fetchMock);
    renderAt("/jobs");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("We could not load jobs");
    expect(alert).toHaveTextContent("ShiftBridge cannot reach the service");
    expect(alert).not.toHaveTextContent("internal details");
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("renders the candidate empty state for an authenticated account", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) return jsonResponse(candidate);
      if (url.includes("/applications/me")) return jsonResponse(pageOf([]));
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderAt("/candidate");

    expect(
      await screen.findByRole("heading", { name: "No applications yet" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Browse open roles" }),
    ).toBeVisible();
  });

  it("blocks a candidate from employer-only routes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(candidate)),
    );
    renderAt("/employer/jobs/new");

    expect(
      await screen.findByRole("heading", { name: "Access denied" }),
    ).toBeVisible();
    expect(screen.getByText(/signed in as a candidate/i)).toBeVisible();
  });

  it("shows a useful page for an unknown route", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(unauthorizedResponse()),
    );
    renderAt("/this-route-does-not-exist");

    expect(
      screen.getByRole("heading", { name: "Page not found" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Browse open roles" }),
    ).toBeVisible();
    await waitFor(() =>
      expect(document.title).toBe("Page not found | ShiftBridge"),
    );
  });
});
