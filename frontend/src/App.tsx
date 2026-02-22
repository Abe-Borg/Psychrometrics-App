import AppLayout from "./components/Layout/AppLayout";
import ToastContainer from "./components/UI/Toast";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";

export default function App() {
  useKeyboardShortcuts();

  return (
    <>
      <AppLayout />
      <ToastContainer />
    </>
  );
}
