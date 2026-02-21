declare module "psychrolib" {
  export const IP: number;
  export const SI: number;
  export function SetUnitSystem(system: number): void;
  export function GetSatVapPres(TDryBulb: number): number;
  export function GetSatHumRatio(TDryBulb: number, Pressure: number): number;
  export function GetHumRatioFromRelHum(TDryBulb: number, RelHum: number, Pressure: number): number;
  export function GetRelHumFromHumRatio(TDryBulb: number, HumRatio: number, Pressure: number): number;
  export function GetTWetBulbFromHumRatio(TDryBulb: number, HumRatio: number, Pressure: number): number;
  export function GetTDewPointFromHumRatio(TDryBulb: number, HumRatio: number, Pressure: number): number;
  export function GetMoistAirEnthalpy(TDryBulb: number, HumRatio: number): number;
  export function GetMoistAirVolume(TDryBulb: number, HumRatio: number, Pressure: number): number;
  export function GetMoistAirDensity(TDryBulb: number, HumRatio: number, Pressure: number): number;
  export function GetStandardAtmPressure(Altitude: number): number;
  export function GetHumRatioFromTWetBulb(TDryBulb: number, TWetBulb: number, Pressure: number): number;
  export function GetHumRatioFromTDewPoint(TDewPoint: number, Pressure: number): number;
  export function GetVapPresFromHumRatio(HumRatio: number, Pressure: number): number;
  export function GetDegreeOfSaturation(TDryBulb: number, HumRatio: number, Pressure: number): number;
}
