import csv
import io
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, Tuple

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.pdfgen import canvas

from app.services import project_service


def generate_project_csv(db: Session, project_id: UUID) -> str:
    """
    Generates a comprehensive CSV export for a project including
    metadata, activity parameters, CPM floats, PERT calculations,
    crashing details, and vendor assignments.
    """
    project = project_service.get_project_or_404(db, project_id)
    network_data = project_service.get_project_network(db, project_id)
    
    # Map network node details by ID
    node_map = {node["id"]: node for node in network_data.get("nodes", []) if node["id"] not in ("START", "END")}

    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Project Summary Header
    writer.writerow(["EVENTPATH PROJECT REPORT - CSV EXPORT"])
    writer.writerow(["Export Date", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
    writer.writerow(["Project ID", str(project.id)])
    writer.writerow(["Project Name", project.name])
    writer.writerow(["Planning Mode", project.mode])
    writer.writerow(["Category", project.category or "N/A"])
    writer.writerow(["Target Completion Date", str(project.target_completion_date) if project.target_completion_date else "N/A"])
    writer.writerow(["Project Description", project.description or "N/A"])
    
    end_node = next((node for node in network_data.get("nodes", []) if node["id"] == "END"), None)
    project_duration = end_node["ef"] if end_node else 0.0
    writer.writerow(["Calculated Duration (Days)", f"{project_duration:.2f}"])
    writer.writerow(["Critical Path", " -> ".join([str(item) for item in network_data.get("critical_path", [])])])
    writer.writerow([])  # Blank row separator

    # 2. Activity Table Headers
    headers = [
        "Activity ID",
        "Activity Name",
        "Duration (Days)",
        "Category",
        "Early Start (ES)",
        "Early Finish (EF)",
        "Late Start (LS)",
        "Late Finish (LF)",
        "Total Float (TF/Slack)",
        "Free Float (FF)",
        "Interfering Float (IF)",
        "Is Critical",
        "Predecessors",
        "Optimistic (t_o)",
        "Most Likely (t_m)",
        "Pessimistic (t_p)",
        "Crash Duration",
        "Normal Cost (INR)",
        "Crash Cost (INR)",
        "Cost Slope (INR/day)",
        "Vendor Name",
        "Vendor Available From",
        "Vendor Available To"
    ]
    writer.writerow(headers)

    # 3. Write Activity Rows
    for act in project.activities:
        node = node_map.get(str(act.id), {})
        
        # Calculate cost slope
        cost_slope = "N/A"
        if act.crash_duration is not None and act.crash_cost is not None and act.normal_cost is not None:
            time_diff = act.duration - act.crash_duration
            if time_diff > 0:
                slope_val = (act.crash_cost - act.normal_cost) / time_diff
                cost_slope = f"{slope_val:.2f}"

        pred_names = ", ".join([p.name for p in act.predecessors]) if act.predecessors else "None"

        row = [
            str(act.id),
            act.name,
            f"{node.get('duration', act.duration):.2f}",
            act.category or "N/A",
            f"{node.get('es', 0.0):.2f}",
            f"{node.get('ef', 0.0):.2f}",
            f"{node.get('ls', 0.0):.2f}",
            f"{node.get('lf', 0.0):.2f}",
            f"{node.get('slack', 0.0):.2f}",
            f"{node.get('free_float', 0.0):.2f}",
            f"{node.get('interfering_float', 0.0):.2f}",
            "YES" if node.get("is_critical", False) else "NO",
            pred_names,
            f"{act.optimistic_time:.2f}" if act.optimistic_time is not None else "N/A",
            f"{act.most_likely_time:.2f}" if act.most_likely_time is not None else "N/A",
            f"{act.pessimistic_time:.2f}" if act.pessimistic_time is not None else "N/A",
            f"{act.crash_duration:.2f}" if act.crash_duration is not None else "N/A",
            f"{act.normal_cost:.2f}" if act.normal_cost is not None else "N/A",
            f"{act.crash_cost:.2f}" if act.crash_cost is not None else "N/A",
            cost_slope,
            act.vendor_name or "N/A",
            str(act.vendor_available_from) if act.vendor_available_from else "N/A",
            str(act.vendor_available_to) if act.vendor_available_to else "N/A"
        ]
        writer.writerow(row)

    return output.getvalue()


class NumberedCanvas(canvas.Canvas):
    """Canvas for adding page numbers and running headers to ReportLab PDF."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 36, 20, page_text)
        self.drawString(36, 20, "EventPath Scheduling Engine — Operational Research Report")

        # Running Top Border
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(36, 750, 612 - 36, 750)
        self.restoreState()


def generate_project_pdf(db: Session, project_id: UUID) -> bytes:
    """
    Generates a publication-grade, styled PDF report of a project using ReportLab.
    Matches executive dashboard typography, color palettes, and structured sections.
    """
    project = project_service.get_project_or_404(db, project_id)
    network_data = project_service.get_project_network(db, project_id)
    
    # Try fetching PERT & Availability if available
    pert_data = None
    if project.mode == "PERT":
        try:
            pert_data = project_service.get_project_pert(db, project_id)
        except Exception:
            pert_data = None

    avail_data = None
    try:
        avail_data = project_service.check_vendor_availability(db, project_id)
    except Exception:
        avail_data = None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#4f46e5")      # Indigo accent
    PRIMARY_DARK = colors.HexColor("#3730a3") 
    TEXT_DARK = colors.HexColor("#0f172a")    # Slate 900
    TEXT_MUTED = colors.HexColor("#64748b")   # Slate 500
    BG_LIGHT = colors.HexColor("#f8fafc")     # Slate 50
    CRITICAL_RED = colors.HexColor("#dc2626") # Red 600
    BORDER_COLOR = colors.HexColor("#e2e8f0")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY_DARK,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=TEXT_MUTED,
        spaceAfter=12
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK
    )
    bold_body_style = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.white
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=TEXT_DARK
    )
    critical_cell_style = ParagraphStyle(
        'CriticalCell',
        parent=table_cell_style,
        fontName='Helvetica-Bold',
        textColor=CRITICAL_RED
    )

    story = []

    # 1. Header Section
    story.append(Paragraph("EventPath Scheduling Engine", subtitle_style))
    story.append(Paragraph(f"Project Report: {project.name}", title_style))
    story.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')} | Mode: <b>{project.mode}</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=14))

    # 2. Executive Summary Block
    end_node = next((n for n in network_data.get("nodes", []) if n["id"] == "END"), None)
    total_duration = end_node["ef"] if end_node else 0.0
    activity_count = len([n for n in network_data.get("nodes", []) if n["id"] not in ("START", "END")])
    critical_count = len([n for n in network_data.get("nodes", []) if n.get("is_critical") and n["id"] not in ("START", "END")])

    summary_data = [
        [
            Paragraph("<b>Total Duration</b>", body_style),
            Paragraph("<b>Total Activities</b>", body_style),
            Paragraph("<b>Critical Activities</b>", body_style),
            Paragraph("<b>Planning Method</b>", body_style),
        ],
        [
            Paragraph(f"<font size=12 color='#4f46e5'><b>{total_duration:.2f} Days</b></font>", body_style),
            Paragraph(f"<font size=12><b>{activity_count}</b></font>", body_style),
            Paragraph(f"<font size=12 color='#dc2626'><b>{critical_count}</b></font>", body_style),
            Paragraph(f"<font size=12><b>{project.mode}</b></font>", body_style),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[135, 135, 135, 135])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BORDER', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # Description & Critical Path
    if project.description:
        story.append(Paragraph(f"<b>Description:</b> {project.description}", body_style))
        story.append(Spacer(1, 4))
    
    crit_path_str = " -> ".join([str(item) for item in network_data.get("critical_path", [])])
    story.append(Paragraph(f"<b>Critical Path Sequence:</b> <font color='#dc2626'><b>{crit_path_str}</b></font>", body_style))
    story.append(Spacer(1, 10))

    # 3. PERT Analysis Section (if PERT mode)
    if project.mode == "PERT" and pert_data:
        story.append(Paragraph("PERT Statistical Analysis (3-Point Estimates)", section_heading))
        prob_str = f"{pert_data.get('probability', 0) * 100:.1f}%" if pert_data.get('probability') is not None else "N/A"
        variance_val = pert_data.get('project_variance', 0.0)
        std_dev = variance_val ** 0.5

        pert_summary = [
            [
                Paragraph("Expected Project Duration", bold_body_style),
                Paragraph(f"{pert_data.get('expected_project_duration', 0.0):.2f} Days", body_style),
                Paragraph("Project Variance (σ²)", bold_body_style),
                Paragraph(f"{variance_val:.2f}", body_style),
            ],
            [
                Paragraph("Standard Deviation (σ)", bold_body_style),
                Paragraph(f"±{std_dev:.2f} Days", body_style),
                Paragraph("Completion Probability", bold_body_style),
                Paragraph(f"<b>{prob_str}</b>", body_style),
            ]
        ]
        pert_table = Table(pert_summary, colWidths=[140, 130, 140, 130])
        pert_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(pert_table)
        story.append(Spacer(1, 10))

    # 4. CPM Schedule & Activity Table
    story.append(Paragraph("CPM Network & Activity Analysis Table", section_heading))
    
    node_map = {n["id"]: n for n in network_data.get("nodes", []) if n["id"] not in ("START", "END")}

    table_data = [[
        Paragraph("Activity", table_header_style),
        Paragraph("Duration", table_header_style),
        Paragraph("ES", table_header_style),
        Paragraph("EF", table_header_style),
        Paragraph("LS", table_header_style),
        Paragraph("LF", table_header_style),
        Paragraph("Total Float", table_header_style),
        Paragraph("Free Float", table_header_style),
        Paragraph("Status", table_header_style),
    ]]

    for act in project.activities:
        node = node_map.get(str(act.id), {})
        is_crit = node.get("is_critical", False)
        
        status_text = Paragraph("<font color='#dc2626'><b>CRITICAL</b></font>", critical_cell_style) if is_crit else Paragraph("<font color='#0284c7'>Flexible</font>", table_cell_style)

        table_data.append([
            Paragraph(f"<b>{act.name}</b>", table_cell_style),
            Paragraph(f"{node.get('duration', act.duration):.1f} d", table_cell_style),
            Paragraph(f"{node.get('es', 0.0):.1f}", table_cell_style),
            Paragraph(f"{node.get('ef', 0.0):.1f}", table_cell_style),
            Paragraph(f"{node.get('ls', 0.0):.1f}", table_cell_style),
            Paragraph(f"{node.get('lf', 0.0):.1f}", table_cell_style),
            Paragraph(f"{node.get('slack', 0.0):.1f}", table_cell_style),
            Paragraph(f"{node.get('free_float', 0.0):.1f}", table_cell_style),
            status_text,
        ])

    activity_table = Table(table_data, colWidths=[120, 48, 42, 42, 42, 42, 56, 56, 70])
    activity_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(activity_table)
    story.append(Spacer(1, 14))

    # 5. Vendor Availability Audit Section (if data present)
    if avail_data:
        story.append(KeepTogether([
            Paragraph("Vendor & Resource Constraints Audit", section_heading),
            Paragraph(
                f"Status: <b>{'⚠️ CONFLICTS DETECTED' if avail_data.get('has_conflicts') else '✅ ALL CONSTRAINTS SATISFIED'}</b> "
                f"({avail_data.get('total_conflicts', 0)} conflicts found)",
                body_style
            ),
            Spacer(1, 6)
        ]))

        conflicts = avail_data.get("conflicts", [])
        if conflicts:
            conf_data = [[
                Paragraph("Conflict Type", table_header_style),
                Paragraph("Activity Name", table_header_style),
                Paragraph("Vendor Name", table_header_style),
                Paragraph("Float Available", table_header_style),
                Paragraph("Resolution Recommendation", table_header_style),
            ]]
            for c in conflicts:
                conf_data.append([
                    Paragraph(f"<b>{c.get('conflict_type')}</b>", table_cell_style),
                    Paragraph(c.get('activity_name', 'N/A'), table_cell_style),
                    Paragraph(c.get('vendor_name', 'N/A'), table_cell_style),
                    Paragraph(f"{c.get('total_float', 0.0):.1f} d", table_cell_style),
                    Paragraph(c.get('resolution_recommendation', 'N/A'), table_cell_style),
                ])
            
            conf_table = Table(conf_data, colWidths=[100, 90, 85, 65, 200])
            conf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#7c3aed")),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(conf_table)
            story.append(Spacer(1, 14))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
