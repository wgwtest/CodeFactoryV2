import { vi } from "vitest";

function createStorageMock(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear: () => {
      values.clear();
    },
    getItem: (key: string) => values.get(String(key)) ?? null,
    key: (index: number) => Array.from(values.keys())[index] ?? null,
    removeItem: (key: string) => {
      values.delete(String(key));
    },
    setItem: (key: string, value: string) => {
      values.set(String(key), String(value));
    }
  };
}

function needsStorageMock(): boolean {
  try {
    return typeof window.localStorage?.setItem !== "function" || typeof window.localStorage?.clear !== "function";
  } catch {
    return true;
  }
}

if (typeof window !== "undefined") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false
    })
  });

  const originalGetComputedStyle = window.getComputedStyle.bind(window);
  window.getComputedStyle = ((element: Element, _pseudoElt?: string) => originalGetComputedStyle(element)) as typeof window.getComputedStyle;

  if (needsStorageMock()) {
    const storageMock = createStorageMock();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      enumerable: true,
      value: storageMock
    });
    vi.stubGlobal("localStorage", storageMock);
  }
}

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal("ResizeObserver", ResizeObserverMock);
