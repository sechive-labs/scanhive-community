import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// Without `test.globals` (deliberately off so `tsc -b` doesn't need
// ambient vitest/jest-dom types across the whole app build), Testing
// Library's automatic afterEach cleanup never registers, so each test's
// rendered tree would otherwise leak into the next one in the same file.
afterEach(() => {
  cleanup();
});

// Recent Node versions define a global `localStorage` that's a no-op unless
// started with --localstorage-file, which shadows jsdom's window.localStorage
// and leaves it undefined. Replace it with a plain in-memory Storage so
// components (theme provider, token storage) work the same as in a real
// browser, without depending on Node startup flags.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

Object.defineProperty(globalThis, "localStorage", {
  value: new MemoryStorage(),
  configurable: true,
  writable: true,
});

// jsdom doesn't implement matchMedia; antd's responsive grid utilities
// (Dropdown, Grid breakpoints, etc.) call it on mount.
if (!window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as unknown as MediaQueryList;
}
