import StatePointForm from "../StatePoint/StatePointForm";
import StatePointList from "../StatePoint/StatePointList";
import ProcessBuilder from "../Process/ProcessBuilder";
import ProcessList from "../Process/ProcessList";
import CoilAnalysis from "../Coil/CoilAnalysis";
import SHRPanel from "../SHR/SHRPanel";
import AirflowCalc from "../Airflow/AirflowCalc";
import DesignDayPanel from "../DesignDay/DesignDayPanel";
import TMYPanel from "../TMY/TMYPanel";
import AHUWizard from "../AHUWizard/AHUWizard";

export default function Sidebar() {
  return (
    <div className="h-full bg-bg-secondary border-l border-border overflow-y-auto">
      <div className="p-4 flex flex-col gap-5">
        {/* Add state point */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            Add State Point
          </h2>
          <StatePointForm />
        </section>

        <div className="h-px bg-border" />

        {/* State point list */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            State Points
          </h2>
          <StatePointList />
        </section>

        <div className="h-px bg-border" />

        {/* Add process */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            Add Process
          </h2>
          <ProcessBuilder />
        </section>

        <div className="h-px bg-border" />

        {/* Process list */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            Processes
          </h2>
          <ProcessList />
        </section>

        <div className="h-px bg-border" />

        {/* Coil analysis */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            Coil Analysis
          </h2>
          <CoilAnalysis />
        </section>

        <div className="h-px bg-border" />

        {/* SHR tools */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            SHR Tools
          </h2>
          <SHRPanel />
        </section>

        <div className="h-px bg-border" />

        {/* Airflow calculator */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            Airflow Calculator
          </h2>
          <AirflowCalc />
        </section>

        <div className="h-px bg-border" />

        {/* AHU Wizard */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            AHU Wizard
          </h2>
          <AHUWizard />
        </section>

        <div className="h-px bg-border" />

        {/* ASHRAE Design Day */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            ASHRAE Design Days
          </h2>
          <DesignDayPanel />
        </section>

        <div className="h-px bg-border" />

        {/* TMY Weather Data */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            TMY Weather Data
          </h2>
          <TMYPanel />
        </section>
      </div>
    </div>
  );
}
