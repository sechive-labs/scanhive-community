import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ResetPasswordPage } from "./ResetPasswordPage";
import { TestProviders } from "../test/testUtils";

vi.mock("../api/authApi", () => ({
  resetPassword: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}));

const { resetPassword } = await import("../api/authApi");

describe("ResetPasswordPage", () => {
  it("shows an invalid-link state when no token is present", () => {
    window.location.hash = "";
    render(<TestProviders><ResetPasswordPage /></TestProviders>);
    expect(screen.getByRole("alert")).toHaveTextContent(/invalid or incomplete/i);
  });

  it("reads the token from the URL fragment, scrubs it, and submits it", async () => {
    window.location.hash = "#token=abc123secret";
    vi.mocked(resetPassword).mockResolvedValue({ message: "ok" });

    render(<TestProviders><ResetPasswordPage /></TestProviders>);

    await waitFor(() => expect(window.location.hash).toBe(""));

    const [first, second] = screen.getAllByPlaceholderText(/characters|re-enter/i);
    await userEvent.type(first, "NewPassword456!");
    await userEvent.type(second, "NewPassword456!");
    await userEvent.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => expect(resetPassword).toHaveBeenCalledWith("abc123secret", "NewPassword456!"));
  });

  it("blocks submission when the passwords differ", async () => {
    window.location.hash = "#token=abc123secret";
    vi.mocked(resetPassword).mockClear();

    render(<TestProviders><ResetPasswordPage /></TestProviders>);

    const [first, second] = screen.getAllByPlaceholderText(/characters|re-enter/i);
    await userEvent.type(first, "NewPassword456!");
    await userEvent.type(second, "Different789!");
    await userEvent.click(screen.getByRole("button", { name: /reset password/i }));

    expect(await screen.findByText(/do not match/i)).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });
});
