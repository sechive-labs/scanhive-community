import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { VerifyEmailPage } from "./VerifyEmailPage";
import { TestProviders } from "../test/testUtils";

vi.mock("../api/authApi", () => ({
  verifyEmail: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}));

const { verifyEmail } = await import("../api/authApi");

describe("VerifyEmailPage", () => {
  it("shows an invalid state when there is no token", () => {
    window.location.hash = "";
    render(<TestProviders><VerifyEmailPage /></TestProviders>);
    expect(screen.getByRole("alert")).toHaveTextContent(/not valid/i);
  });

  it("does not spend the token on load; only on an explicit click, then scrubs the URL", async () => {
    window.location.hash = "#token=verifytoken123";
    vi.mocked(verifyEmail).mockResolvedValue({ message: "Your email address is verified." });

    render(<TestProviders><VerifyEmailPage /></TestProviders>);
    await waitFor(() => expect(window.location.hash).toBe(""));
    expect(verifyEmail).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /verify my email/i }));

    await waitFor(() => expect(verifyEmail).toHaveBeenCalledWith("verifytoken123"));
    expect(await screen.findByText(/email verified/i)).toBeInTheDocument();
  });
});
