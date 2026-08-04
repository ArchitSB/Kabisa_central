import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = { children: ReactNode };
type State = { failed: boolean };

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error("Kabisa admin render error", error, info.componentStack);
    }
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-6">
        <section
          className="surface-card w-full max-w-lg p-8 text-center"
          aria-labelledby="application-error-title"
        >
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-danger-surface text-danger">
            <AlertTriangle aria-hidden="true" className="size-6" />
          </span>
          <h1
            id="application-error-title"
            className="mt-5 font-display text-2xl font-semibold"
          >
            The workspace needs to reload
          </h1>
          <p className="mt-2 text-sm leading-6 text-secondary">
            An unexpected display error occurred. Your saved server data is unaffected.
          </p>
          <Button className="mt-6" onClick={() => window.location.reload()}>
            Reload workspace
          </Button>
        </section>
      </main>
    );
  }
}
