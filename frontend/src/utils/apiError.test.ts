import { AxiosError } from "axios";
import { describe, expect, it } from "vitest";

import { getApiErrorMessage } from "./apiError";

function validationError(detail: unknown[]) {
  return new AxiosError("bad", "ERR_BAD_REQUEST", undefined, undefined, {
    status: 422, statusText: "", headers: {}, config: {} as never, data: { detail },
  });
}

describe("getApiErrorMessage validation formatting", () => {
  it("shows our password-policy sentence without the pydantic prefix", () => {
    const message = getApiErrorMessage(validationError([{
      type: "value_error", loc: ["body", "password"],
      msg: "Value error, That password is too common and easy to guess. Try a longer passphrase.",
    }]));
    expect(message).toBe("That password is too common and easy to guess. Try a longer passphrase.");
  });

  it("turns 'too short' into a plain sentence", () => {
    const message = getApiErrorMessage(validationError([{
      type: "string_too_short", loc: ["body", "password"], msg: "String should have at least 8 characters",
      ctx: { min_length: 8 },
    }]));
    expect(message).toBe("Password must be at least 8 characters.");
  });
});
