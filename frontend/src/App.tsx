import { Component, type ReactNode, type ErrorInfo } from "react";
import AppLayout from "./components/Layout/AppLayout";
import ToastContainer from "./components/UI/Toast";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("React render error:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          background: "#0f1117",
          color: "#e8eaf0",
          fontFamily: "system-ui, sans-serif",
          padding: "2rem",
        }}>
          <h1 style={{ fontSize: "1.5rem", marginBottom: "1rem", color: "#ff6b6b" }}>
            Something went wrong
          </h1>
          <pre style={{
            background: "#1a1d27",
            padding: "1rem",
            borderRadius: "0.5rem",
            maxWidth: "600px",
            overflow: "auto",
            fontSize: "0.875rem",
            color: "#f5725b",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}>
            {this.state.error?.message}
            {"\n\n"}
            {this.state.error?.stack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: "1.5rem",
              padding: "0.5rem 1.5rem",
              background: "#5b9cf5",
              color: "#fff",
              border: "none",
              borderRadius: "0.25rem",
              cursor: "pointer",
              fontSize: "0.875rem",
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  useKeyboardShortcuts();

  return (
    <ErrorBoundary>
      <AppLayout />
      <ToastContainer />
    </ErrorBoundary>
  );
}
