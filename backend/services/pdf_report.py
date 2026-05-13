from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import os

os.makedirs("reports", exist_ok=True)

# ── Color palette ─────────────────────────────────────────────────
PRIMARY     = colors.HexColor("#1E50A0")
PRIMARY_LIGHT = colors.HexColor("#E8F0FB")
ACCENT      = colors.HexColor("#2E86AB")
SUCCESS     = colors.HexColor("#2D6A4F")
WARNING     = colors.HexColor("#B5451B")
LIGHT_GRAY  = colors.HexColor("#F5F5F5")
MID_GRAY    = colors.HexColor("#CCCCCC")
DARK_GRAY   = colors.HexColor("#333333")
WHITE       = colors.white


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            fontSize=22, fontName="Helvetica-Bold",
            textColor=WHITE, alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontSize=11, fontName="Helvetica",
            textColor=WHITE, alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "section",
            fontSize=13, fontName="Helvetica-Bold",
            textColor=PRIMARY, spaceBefore=12, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10, fontName="Helvetica",
            textColor=DARK_GRAY, spaceAfter=4, leading=15,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            fontSize=10, fontName="Helvetica-Bold",
            textColor=DARK_GRAY, spaceAfter=4,
        ),
        "location_title": ParagraphStyle(
            "location_title",
            fontSize=11, fontName="Helvetica-Bold",
            textColor=PRIMARY, spaceBefore=8, spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontSize=10, fontName="Helvetica",
            textColor=DARK_GRAY, leftIndent=12,
            spaceAfter=3, leading=14,
        ),
        "placeholder": ParagraphStyle(
            "placeholder",
            fontSize=10, fontName="Helvetica-Oblique",
            textColor=colors.HexColor("#888888"),
            alignment=TA_CENTER, spaceBefore=10, spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontSize=8, fontName="Helvetica",
            textColor=colors.HexColor("#888888"),
            alignment=TA_CENTER,
        ),
        "road_good": ParagraphStyle(
            "road_good",
            fontSize=10, fontName="Helvetica",
            textColor=SUCCESS, spaceAfter=3,
        ),
        "road_warn": ParagraphStyle(
            "road_warn",
            fontSize=10, fontName="Helvetica",
            textColor=WARNING, spaceAfter=3,
        ),
    }


def _header(story, styles, location, lat, lon, radius_km):
    # Blue header banner using a table
    header_data = [[
        Paragraph("GIS Site Analysis Report", styles["title"]),
    ]]
    header_table = Table(header_data, colWidths=[170 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), PRIMARY),
        ("TOPPADDING",  (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # Location detail strip
    detail_data = [[
        Paragraph(f"<b>Location:</b> {location}", styles["body"]),
        Paragraph(f"<b>Coordinates:</b> {lat:.4f}, {lon:.4f}", styles["body"]),
        Paragraph(f"<b>Radius:</b> {radius_km} km", styles["body"]),
        Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%d %b %Y, %H:%M')}", styles["body"]),
    ]]
    detail_table = Table(detail_data, colWidths=[50 * mm, 50 * mm, 35 * mm, 45 * mm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PRIMARY_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GRAY),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 6 * mm))


def _poi_summary_section(story, styles, summary):
    story.append(Paragraph("Area Overview — Points of Interest", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 3 * mm))

    # Map your actual summary keys to display names
    category_map = [
        ("Health Care",    "Hospitals & Clinics"),
        ("Education",      "Schools & Colleges"),
        ("Transport",      "Transport Hubs"),
        ("Food",           "Restaurants & Food"),
        ("Shops",          "Shops & Retail"),
        ("Business",       "Businesses"),
        ("Finance",        "Finance & Banking"),
        ("Recreation",     "Recreation & Parks"),
        ("Tourism",        "Tourism & Hotels"),
        ("Religious",      "Religious Places"),
        ("Infrastructure", "Infrastructure"),
        ("Building",       "Buildings & Offices"),
    ]

    # Table header
    table_data = [[
        Paragraph("<b>Category</b>", styles["body_bold"]),
        Paragraph("<b>Count</b>",    styles["body_bold"]),
        Paragraph("<b>Availability</b>", styles["body_bold"]),
    ]]

    for key, display in category_map:
        count = summary.get(key, 0)
        if count > 100:   avail = "High"
        elif count > 30:  avail = "Moderate"
        elif count > 0:   avail = "Low"
        else:             avail = "None"

        table_data.append([
            Paragraph(display, styles["body"]),
            Paragraph(str(count), styles["body"]),
            Paragraph(avail, styles["body"]),
        ])

    poi_table = Table(table_data, colWidths=[80 * mm, 30 * mm, 60 * mm])
    poi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, MID_GRAY),
        # Alternating rows
        *[("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY)
          for i in range(2, len(table_data), 2)],
    ]))
    story.append(poi_table)
    story.append(Spacer(1, 6 * mm))


def _road_summary_section(story, styles, summary):
    story.append(Paragraph("Road Network Overview", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 3 * mm))

    grids_with_road   = summary.get("grids_with_road", 0)
    total_grids       = summary.get("total_grids", 0)
    primary_coverage  = summary.get("primary_coverage_pct", 0)
    secondary_coverage= summary.get("secondary_coverage_pct", 0)
    avg_density       = summary.get("avg_road_density", 0)

    road_data = [
        [Paragraph("<b>Metric</b>", styles["body_bold"]),
         Paragraph("<b>Value</b>",  styles["body_bold"])],
        [Paragraph("Grids with road network", styles["body"]),
         Paragraph(f"{grids_with_road} / {total_grids}", styles["body"])],
        [Paragraph("Primary road coverage", styles["body"]),
         Paragraph(f"{primary_coverage:.1f}% of grids", styles["body"])],
        [Paragraph("Secondary road coverage", styles["body"]),
         Paragraph(f"{secondary_coverage:.1f}% of grids", styles["body"])],
        [Paragraph("Average road density", styles["body"]),
         Paragraph(f"{avg_density:.0f} m/km²", styles["body"])],
    ]

    road_table = Table(road_data, colWidths=[100 * mm, 70 * mm])
    road_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, MID_GRAY),
        *[("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY)
          for i in range(2, len(road_data), 2)],
    ]))
    story.append(road_table)
    story.append(Spacer(1, 6 * mm))


def _suggestions_section(story, styles, suggestions):
    story.append(Paragraph("Top 3 Recommended Locations", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 3 * mm))

    if not suggestions:
        story.append(Paragraph(
            "No location recommendations generated yet.\n"
            "Ask the chatbot for a location suggestion first, then regenerate this report.",
            styles["placeholder"]
        ))
        story.append(Spacer(1, 4 * mm))
        return

    for s in suggestions:
        rank           = s.get("rank", "?")
        lat            = s.get("lat", 0)
        lon            = s.get("lon", 0)
        score          = s.get("score", 0)
        population     = s.get("population", 0)
        road_desc      = s.get("road_desc", "No road data available")
        primary_len    = s.get("primary_length",   0) or 0
        secondary_len  = s.get("secondary_length", 0) or 0
        dist_primary   = s.get("dist_to_primary")
        dist_secondary = s.get("dist_to_secondary")
        road_density   = s.get("road_density",     0) or 0

        # Road quality label
        if primary_len > 0 and secondary_len > 0:
            road_quality = "EXCELLENT — direct access to both primary and secondary roads"
            rq_style     = styles["road_good"]
        elif primary_len > 0:
            road_quality = "GOOD — primary road passes directly through"
            rq_style     = styles["road_good"]
        elif secondary_len > 0:
            dist_str     = f"{dist_primary:.0f}m away" if dist_primary is not None else "unknown"
            road_quality = f"MODERATE — secondary road present, nearest primary road {dist_str}"
            rq_style     = styles["body"]
        else:
            dist_str     = f"{dist_primary:.0f}m" if dist_primary is not None else "unknown"
            road_quality = f"LIMITED — no direct road, nearest primary road {dist_str}"
            rq_style     = styles["road_warn"]

        # Population label
        if population > 5000:   pop_label = "HIGH density"
        elif population > 2000: pop_label = "MEDIUM density"
        else:                   pop_label = "LOW density"

        # Location header row
        loc_header = [[
            Paragraph(
                f"Location {rank} — {lat:.5f}, {lon:.5f}   |   Score: {score:.2f}",
                ParagraphStyle(
                    "loc_hdr",
                    fontSize=11, fontName="Helvetica-Bold",
                    textColor=WHITE,
                )
            )
        ]]
        loc_hdr_table = Table(loc_header, colWidths=[170 * mm])
        loc_hdr_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), ACCENT),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(loc_hdr_table)

        # Detail table
        detail_rows = [
            [Paragraph("<b>Population coverage</b>", styles["body"]),
             Paragraph(f"{population:,} ({pop_label} area)", styles["body"])],
            [Paragraph("<b>Road access</b>", styles["body"]),
             Paragraph(road_desc, styles["body"])],
            [Paragraph("<b>Road quality</b>", styles["body"]),
             Paragraph(road_quality, rq_style)],
            [Paragraph("<b>Road density</b>", styles["body"]),
             Paragraph(f"{road_density:.0f} m/km²", styles["body"])],
        ]

        if primary_len > 0:
            detail_rows.append([
                Paragraph("<b>Primary road length inside grid</b>", styles["body"]),
                Paragraph(f"{primary_len:.0f} m", styles["body"]),
            ])
        if secondary_len > 0:
            detail_rows.append([
                Paragraph("<b>Secondary road length inside grid</b>", styles["body"]),
                Paragraph(f"{secondary_len:.0f} m", styles["body"]),
            ])
        if dist_primary is not None and primary_len == 0:
            detail_rows.append([
                Paragraph("<b>Distance to nearest primary road</b>", styles["body"]),
                Paragraph(f"{dist_primary:.0f} m", styles["body"]),
            ])
        if dist_secondary is not None and secondary_len == 0:
            detail_rows.append([
                Paragraph("<b>Distance to nearest secondary road</b>", styles["body"]),
                Paragraph(f"{dist_secondary:.0f} m", styles["body"]),
            ])

        detail_table = Table(detail_rows, colWidths=[80 * mm, 90 * mm])
        detail_table.setStyle(TableStyle([
            ("FONTSIZE",      (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.4, MID_GRAY),
            *[("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY)
              for i in range(0, len(detail_rows), 2)],
        ]))
        story.append(detail_table)
        story.append(Spacer(1, 5 * mm))


def _footer(story, styles):
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"Generated by GIS Site Intelligence System  |  {datetime.now().strftime('%d %B %Y')}",
        styles["footer"]
    ))


# ── Main function ─────────────────────────────────────────────────
def generate_pdf(
    location:     str,
    lat:          float,
    lon:          float,
    radius_km:    float,
    summary:      dict,
    suggestions:  list = None,
    road_summary: dict = None,
) -> str:

    suggestions  = suggestions  or []
    road_summary = road_summary or {}

    path = "reports/site_report.pdf"
    doc  = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = _styles()
    story  = []

    _header(story, styles, location, lat, lon, radius_km)
    _poi_summary_section(story, styles, summary)
    _road_summary_section(story, styles, road_summary)
    _suggestions_section(story, styles, suggestions)
    _footer(story, styles)

    doc.build(story)
    return path