import Toolbar from "./Toolbar";
import Sidebar from "./Sidebar";
import PsychroChart from "../Chart/PsychroChart";

export default function AppLayout() {
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

        {/* Sidebar — fixed width */}
        <div className="w-80 flex-shrink-0">
          <Sidebar />
        </div>
      </div>
    </div>
  );
}
