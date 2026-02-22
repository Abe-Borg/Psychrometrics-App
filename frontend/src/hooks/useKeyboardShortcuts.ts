import { useEffect } from "react";
import { useStore } from "../store/useStore";
import { downloadJSON } from "../utils/exportHelpers";

export function useKeyboardShortcuts() {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const isMod = e.metaKey || e.ctrlKey;

      // Ignore shortcuts when typing in inputs/textareas
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      // Ctrl/Cmd+Z → undo
      if (isMod && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        useStore.getState().undo();
        return;
      }

      // Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y → redo
      if ((isMod && e.key === "z" && e.shiftKey) || (isMod && e.key === "y")) {
        e.preventDefault();
        useStore.getState().redo();
        return;
      }

      // Ctrl/Cmd+S → save project
      if (isMod && e.key === "s") {
        e.preventDefault();
        const state = useStore.getState();
        const data = state.exportProject();
        const filename = `${data.title.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
        downloadJSON(data, filename);
        state.addToast("Project saved", "success");
        return;
      }

      // Delete/Backspace → remove selected state point
      if (e.key === "Delete" || e.key === "Backspace") {
        const state = useStore.getState();
        if (state.selectedPointIndex !== null) {
          e.preventDefault();
          state.removeStatePoint(state.selectedPointIndex);
          state.setSelectedPointIndex(null);
        }
        return;
      }

      // Escape → deselect
      if (e.key === "Escape") {
        useStore.getState().setSelectedPointIndex(null);
        return;
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);
}
