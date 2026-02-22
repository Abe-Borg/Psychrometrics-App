import Plotly from "plotly.js";

export function downloadJSON(data: object, filename: string): void {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  triggerDownload(blob, filename);
}

export function downloadCSV(headers: string[], rows: string[][], filename: string): void {
  const escape = (val: string) => {
    if (val.includes(",") || val.includes('"') || val.includes("\n")) {
      return `"${val.replace(/"/g, '""')}"`;
    }
    return val;
  };
  const lines = [
    headers.map(escape).join(","),
    ...rows.map((row) => row.map(escape).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  triggerDownload(blob, filename);
}

export async function downloadChartImage(
  plotDiv: HTMLElement,
  format: "png" | "svg",
  filename: string,
): Promise<void> {
  await Plotly.downloadImage(plotDiv as Plotly.PlotlyHTMLElement, {
    format,
    filename,
    width: 1600,
    height: 900,
  });
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
