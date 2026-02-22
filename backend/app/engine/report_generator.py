"""
PDF report generator using fpdf2.

Produces a professional multi-page PDF report containing:
  - Title page with project info and chart image
  - State points table
  - Processes summary table
  - Coil analysis results
  - SHR results
  - User notes
"""

import base64
import io
import tempfile
import os
from datetime import datetime

from fpdf import FPDF

from app.models.report import ReportInput


# Property columns for state points table
_SP_COLS_IP = [
    ("Label", 24),
    ("Tdb °F", 14),
    ("Twb °F", 14),
    ("Tdp °F", 14),
    ("RH %", 12),
    ("W gr/lb", 16),
    ("h BTU/lb", 16),
    ("v ft³/lb", 16),
]

_SP_COLS_SI = [
    ("Label", 24),
    ("Tdb °C", 14),
    ("Twb °C", 14),
    ("Tdp °C", 14),
    ("RH %", 12),
    ("W g/kg", 16),
    ("h kJ/kg", 16),
    ("v m³/kg", 16),
]

# Process summary columns
_PROC_COLS = [
    ("Type", 36),
    ("Start Tdb", 18),
    ("End Tdb", 18),
    ("Start W", 18),
    ("End W", 18),
    ("Qs", 16),
    ("Ql", 16),
    ("Qt", 16),
    ("SHR", 14),
]


class PsychroReport(FPDF):
    """Custom FPDF subclass with header/footer."""

    def __init__(self, title: str):
        super().__init__(orientation="L", unit="mm", format="letter")
        self._report_title = title
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, self._report_title, align="L")
        self.cell(0, 6, datetime.now().strftime("%Y-%m-%d %H:%M"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_report(inp: ReportInput) -> bytes:
    """Generate a PDF report and return the bytes."""
    pdf = PsychroReport(inp.title)
    pdf.alias_nb_pages()

    is_ip = inp.unit_system.value == "IP"

    # ── Page 1: Title + Chart ──
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, inp.title, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Project info
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    unit_label = "IP (°F, BTU, grains)" if is_ip else "SI (°C, kJ, g/kg)"
    pressure_label = f"{inp.pressure:.3f} {'psia' if is_ip else 'Pa'}"
    altitude_label = f"{inp.altitude:.0f} {'ft' if is_ip else 'm'}"

    info_lines = [
        f"Unit System: {unit_label}",
        f"Pressure: {pressure_label}   |   Altitude: {altitude_label}",
        f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
    ]
    for line in info_lines:
        pdf.cell(0, 6, line, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Chart image
    if "chart" in inp.include_sections and inp.chart_image_base64:
        _add_chart_image(pdf, inp.chart_image_base64)

    # ── State Points Table ──
    if "state_points" in inp.include_sections and inp.state_points:
        pdf.add_page()
        _add_section_heading(pdf, "State Points")
        _add_state_points_table(pdf, inp.state_points, is_ip)

    # ── Processes Table ──
    if "processes" in inp.include_sections and inp.processes:
        pdf.add_page()
        _add_section_heading(pdf, "Processes")
        _add_processes_table(pdf, inp.processes, is_ip)

    # ── Coil Results ──
    if "coil" in inp.include_sections and inp.coil_result:
        pdf.add_page()
        _add_section_heading(pdf, "Coil Analysis")
        _add_coil_results(pdf, inp.coil_result, is_ip)

    # ── SHR Results ──
    if "shr" in inp.include_sections and (inp.shr_lines or inp.gshr_result):
        pdf.add_page()
        _add_section_heading(pdf, "SHR Analysis")
        _add_shr_results(pdf, inp.shr_lines, inp.gshr_result, is_ip)

    # ── Notes ──
    if "notes" in inp.include_sections and inp.notes:
        pdf.add_page()
        _add_section_heading(pdf, "Notes")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5, inp.notes)

    return pdf.output()


def _add_chart_image(pdf: FPDF, b64_data: str) -> None:
    """Decode base64 PNG and add to PDF."""
    # Strip data URI prefix if present
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]

    img_bytes = base64.b64decode(b64_data)

    # Write to a temp file (fpdf2 needs a file path or BytesIO)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    try:
        tmp.write(img_bytes)
        tmp.flush()
        tmp.close()

        # Landscape letter: usable width ~257mm, height ~170mm (accounting for margins/header)
        available_width = pdf.w - 20  # 10mm margins each side
        available_height = pdf.h - pdf.get_y() - 20

        pdf.image(tmp.name, x=10, w=available_width, h=min(available_height, 120))
    finally:
        os.unlink(tmp.name)


def _add_section_heading(pdf: FPDF, text: str) -> None:
    """Add a section heading."""
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _add_state_points_table(pdf: FPDF, points: list[dict], is_ip: bool) -> None:
    """Render the state points table."""
    cols = _SP_COLS_IP if is_ip else _SP_COLS_SI

    # Header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_text_color(30, 30, 30)
    for label, width in cols:
        pdf.cell(width, 6, label, border=1, fill=True, align="C")
    pdf.ln()

    # Rows
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(40, 40, 40)
    for pt in points:
        label = str(pt.get("label", ""))[:12]
        tdb = _fv(pt.get("Tdb"))
        twb = _fv(pt.get("Twb"))
        tdp = _fv(pt.get("Tdp"))
        rh = _fv(pt.get("RH"))
        w_display = _fv(pt.get("W_display"))
        h = _fv(pt.get("h"))
        v = _fv(pt.get("v"))

        vals = [label, tdb, twb, tdp, rh, w_display, h, v]
        for i, (_, width) in enumerate(cols):
            align = "L" if i == 0 else "C"
            pdf.cell(width, 5, vals[i], border=1, align=align)
        pdf.ln()


def _add_processes_table(pdf: FPDF, processes: list[dict], is_ip: bool) -> None:
    """Render the process summary table."""
    # Header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_text_color(30, 30, 30)
    for label, width in _PROC_COLS:
        pdf.cell(width, 6, label, border=1, fill=True, align="C")
    pdf.ln()

    # Rows
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(40, 40, 40)
    for proc in processes:
        ptype = str(proc.get("process_type", "")).replace("_", " ").title()[:20]
        start = proc.get("start_point", {})
        end = proc.get("end_point", {})
        meta = proc.get("metadata", {})

        vals = [
            ptype,
            _fv(start.get("Tdb")),
            _fv(end.get("Tdb")),
            _fv(start.get("W_display")),
            _fv(end.get("W_display")),
            _fv(meta.get("Qs")),
            _fv(meta.get("Ql")),
            _fv(meta.get("Qt")),
            _fv(meta.get("SHR")),
        ]
        for i, (_, width) in enumerate(_PROC_COLS):
            align = "L" if i == 0 else "C"
            pdf.cell(width, 5, vals[i], border=1, align=align)
        pdf.ln()


def _add_coil_results(pdf: FPDF, coil: dict, is_ip: bool) -> None:
    """Render coil analysis results."""
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)

    load_unit = "BTU/lb" if is_ip else "kJ/kg"
    temp_unit = "°F" if is_ip else "°C"

    entering = coil.get("entering", {})
    leaving = coil.get("leaving", {})
    adp = coil.get("adp", {})

    lines = [
        f"Mode: {coil.get('mode', 'N/A')}",
        f"Entering: {_fv(entering.get('Tdb'))}{temp_unit} DB / {_fv(entering.get('W_display'))} {'gr/lb' if is_ip else 'g/kg'}",
        f"Leaving: {_fv(leaving.get('Tdb'))}{temp_unit} DB / {_fv(leaving.get('W_display'))} {'gr/lb' if is_ip else 'g/kg'}",
        f"ADP: {_fv(adp.get('Tdb'))}{temp_unit}",
        f"Bypass Factor: {_fv(coil.get('bypass_factor'))}   |   Contact Factor: {_fv(coil.get('contact_factor'))}",
        f"",
        f"Sensible Load (Qs): {_fv(coil.get('Qs'))} {load_unit}",
        f"Latent Load (Ql): {_fv(coil.get('Ql'))} {load_unit}",
        f"Total Load (Qt): {_fv(coil.get('Qt'))} {load_unit}",
        f"SHR: {_fv(coil.get('SHR'))}",
    ]

    gpm = coil.get("gpm")
    if gpm is not None:
        lines.append(f"Water Flow: {_fv(gpm)} GPM")

    for line in lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")


def _add_shr_results(pdf: FPDF, shr_lines: list[dict], gshr: dict | None, is_ip: bool) -> None:
    """Render SHR analysis results."""
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)

    if shr_lines:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "SHR Lines", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for i, line in enumerate(shr_lines):
            room = line.get("room_point", {})
            pdf.cell(
                0, 5,
                f"Line {i+1}: SHR = {_fv(line.get('shr'))} | "
                f"Room: {_fv(room.get('Tdb'))}{'°F' if is_ip else '°C'} | "
                f"ADP: {_fv(line.get('adp_Tdb'))}{'°F' if is_ip else '°C'}",
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(3)

    if gshr:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Grand SHR (GSHR) Analysis", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        lines = [
            f"Room SHR: {_fv(gshr.get('room_shr'))}",
            f"GSHR: {_fv(gshr.get('gshr'))}",
        ]
        eshr = gshr.get("eshr")
        if eshr is not None:
            lines.append(f"ESHR: {_fv(eshr)}")
        for line in lines:
            pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")


def _fv(val, decimals: int = 2) -> str:
    """Format a value for display, handling None gracefully."""
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.{decimals}f}"
    return str(val)
