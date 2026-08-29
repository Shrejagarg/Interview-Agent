import { type ReactElement, type ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";

function AllProviders({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

export function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

export { customRender as render };
export * from "@testing-library/react";