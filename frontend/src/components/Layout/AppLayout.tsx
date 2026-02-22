import { useState, useCallback, useRef, useEffect } from "react";
import Toolbar from "./Toolbar";
import Sidebar from "./Sidebar";
import PsychroChart from "../Chart/PsychroChart";

const MIN_WIDTH = 240;
const MAX_WIDTH = 500;
const DEFAULT_WIDTH = 320;

export default function AppLayout() {
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_WIDTH);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const isDragging = useRef(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    function handleMouseMove(e: MouseEvent) {
      if (!isDragging.current) return;
      const newWidth = window.innerWidth - e.clientX;
      setSidebarWidth(Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, newWidth)));
    }

    function handleMouseUp() {
      if (isDragging.current) {
        isDragging.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    }

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  return (
    <div className="flex flex-col h-screen">
      {/* Top toolbar */}
      <Toolbar />

      {/* Main content area */}
      <div className="flex flex-1 min-h-0">
        {/* Chart — takes most of the space */}
        <div className="flex-1 min-w-0">
          <PsychroChart />
        </div>

        {/* Drag handle */}
        <div
          className="drag-handle w-1 flex-shrink-0 bg-border hover:bg-accent cursor-col-resize
                     flex items-center justify-center relative group transition-colors"
          onMouseDown={handleMouseDown}
        >
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="absolute z-10 w-5 h-8 bg-bg-secondary border border-border rounded-sm
                       text-text-muted hover:text-text-primary text-xs flex items-center justify-center
                       cursor-pointer transition-colors"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? "\u25C0" : "\u25B6"}
          </button>
        </div>

        {/* Sidebar — resizable */}
        {!isCollapsed && (
          <div className="sidebar-panel flex-shrink-0" style={{ width: sidebarWidth }}>
            <Sidebar />
          </div>
        )}
      </div>
    </div>
  );
}
