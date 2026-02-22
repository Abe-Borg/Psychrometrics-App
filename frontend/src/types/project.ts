import type { UnitSystem, StatePointOutput, ProcessOutput, CoilOutput, SHRLineOutput, GSHROutput } from "./psychro";

export interface ProjectFile {
  version: "1.0";
  title: string;
  savedAt: string;
  unitSystem: UnitSystem;
  pressure: number;
  altitude: number;
  statePoints: StatePointOutput[];
  processes: ProcessOutput[];
  coilResult: CoilOutput | null;
  shrLines: SHRLineOutput[];
  gshrResult: GSHROutput | null;
}
