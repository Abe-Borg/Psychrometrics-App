import StatePointForm from "../StatePoint/StatePointForm";
import StatePointList from "../StatePoint/StatePointList";

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
      </div>
    </div>
  );
}
