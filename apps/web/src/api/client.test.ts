import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, ApiNetworkError, api, parseProblemDetails } from "./client";
import { candidate, jsonResponse } from "../test/fixtures";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("API client", () => {
  it("sends login through the cookie-authenticated API boundary", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ user: candidate }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.login({
        email: "candidate@shiftbridge.test",
        password: "ShiftBridge-Demo-2026!",
      }),
    ).resolves.toEqual(candidate);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, options] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/auth/login");
    expect(options).toEqual(
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
    expect(JSON.parse(String(options?.body))).toEqual({
      email: "candidate@shiftbridge.test",
      password: "ShiftBridge-Demo-2026!",
    });
  });

  it("turns problem details into a typed API error with field context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        jsonResponse(
          {
            code: "VALIDATION_ERROR",
            title: "Validation failed",
            status: 422,
            detail: "One or more fields are invalid.",
            request_id: "validation-request",
            field_errors: [
              {
                field: "email",
                message: "Enter a valid email.",
                type: "value_error",
              },
            ],
          },
          422,
        ),
      ),
    );

    const error = await api.me().catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      requestId: "validation-request",
      fieldErrors: [{ field: "email", message: "Enter a valid email." }],
    });
  });

  it("safely normalizes a malformed non-JSON problem response", () => {
    expect(
      parseProblemDetails("<html>unavailable</html>", 503, "request-503"),
    ).toEqual({
      code: "HTTP_ERROR",
      title: "Request failed",
      status: 503,
      detail: "The service returned an unexpected response.",
      request_id: "request-503",
    });
  });

  it("reports an unreachable service without exposing fetch internals", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockRejectedValue(new TypeError("connection refused")),
    );

    const error = await api.jobs().catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiNetworkError);
    expect(error).toMatchObject({ code: "NETWORK_UNREACHABLE" });
    expect((error as Error).message).not.toContain("connection refused");
  });
});
