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
            textColor=PRIMARY, spaceBefore=6, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10, fontName="Helvetica",
            textColor=DARK_GRAY, spaceAfter=4, leading=13,
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

    # ── Title Banner ─────────────────────────────────
    title_para = Paragraph(
        """
        <para align="center">
        <font color="white"><b>GIS Site Analysis Report</b></font>
        </para>
        """,
        ParagraphStyle(
            "header_title",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=0,
            spaceBefore=0,
        )
    )

    header_table = Table(
        [[title_para]],
        colWidths=[170 * mm],
        hAlign="CENTER"
    )

    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),

        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),

        # IMPORTANT FIX
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),

        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 3 * mm))

    # ── Row 1 : Location ────────────────────────────
    location_table = Table(
        [[
            Paragraph(
                f"<b>Location:</b> {location}",
                styles["body"]
            )
        ]],
        colWidths=[170 * mm],
        hAlign="CENTER"
    )

    location_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_LIGHT),

        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),

        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),

        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(location_table)
    story.append(Spacer(1, 1 * mm))

    # ── Row 2 : Coordinates + Radius ────────────────
    detail_table = Table(
        [[
            Paragraph(
                f"<b>Coordinates:</b> {lat:.4f}, {lon:.4f}",
                styles["body"]
            ),

            Paragraph(
                f"<b>Radius:</b> {radius_km} km",
                styles["body"]
            ),
        ]],
        colWidths=[110 * mm, 60 * mm],
        hAlign="CENTER"
    )

    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_LIGHT),

        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),

        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),

        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.3, MID_GRAY),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(detail_table)

    story.append(Spacer(1, 4 * mm))
 

def _poi_summary_section(story, styles, summary):

    story.append(Paragraph("Area Overview — Points of Interest", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 2 * mm))
    category_map = [
        ("Health Care",    "Health Care"),
        ("Education",      "Education"),
        ("Transport",      "Transport"),
        ("Food",           "Food"),
        ("Shops",          "Shops"),
        ("Business",       "Businesses"),
        ("Finance",        "Finance"),
        ("Recreation",     "Recreation"),
        ("Tourism",        "Tourism"),
        ("Religious",      "Religious"),
        ("Infrastructure", "Infrastructure"),
        ("Building",       "Buildings"),
    ]

    # ── Table Header ───────────────────────────────
    table_data = [[
        Paragraph(
            '<font color="white"><b>Category</b></font>',
            styles["body_bold"]
        ),

        Paragraph(
            '<font color="white"><b>Count</b></font>',
            styles["body_bold"]
        ),
    ]]

    # ── Rows ───────────────────────────────────────
    for key, display in category_map:

        count = summary.get(key, 0)

        table_data.append([
            Paragraph(display, styles["body"]),
            Paragraph(str(count), styles["body"]),
        ])

    # ── Table ──────────────────────────────────────
    poi_table = Table(
        table_data,
        colWidths=[120 * mm, 50 * mm]
    )

    poi_table.setStyle(TableStyle([

        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),

        # Text color white
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("FONTSIZE", (0, 0), (-1, -1), 10),

        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

        ("LEFTPADDING", (0, 0), (-1, -1), 8),

        ("GRID", (0, 0), (-1, -1), 0.4, MID_GRAY),

        # Alternate row colors
        *[
            ("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY)
            for i in range(2, len(table_data), 2)
        ],
    ]))

    story.append(poi_table)

    story.append(Spacer(1, 4 * mm))


def _road_summary_section(story, styles, road_summary):
    story.append(Paragraph("Road Network Overview", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 2 * mm))

    grids_with_road   = road_summary.get("grids_with_road", 0)
    total_grids       = road_summary.get("total_grids", 0)
    primary_coverage  = road_summary.get("primary_coverage_pct", 0)
    secondary_coverage= road_summary.get("secondary_coverage_pct", 0)
    avg_density       = road_summary.get("avg_road_density", 0)

    road_data = [
       [Paragraph('<font color="white"><b>Metric</b></font>',styles["body_bold"]),
        Paragraph('<font color="white"><b>Value</b></font>',styles["body_bold"])],
       
        [Paragraph("Grids with road network out of total", styles["body"]),
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
    story.append(Spacer(1, 4 * mm))



def _suggestions_section(story, styles, suggestions):

    story.append(Paragraph("Top 3 Recommended Locations", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 1 * mm))

    # ── No Suggestions Case ─────────────────────────
    if not suggestions:

        story.append(Paragraph(
            "No location recommendations generated yet.<br/>"
            "Ask the chatbot for a location suggestion first, then regenerate this report.",
            styles["placeholder"]
        ))

        # VERY SMALL SPACE ONLY
        story.append(Spacer(1, 1 * mm))

        return

    # ── Suggestions Available ───────────────────────
    for s in suggestions:

        rank           = s.get("rank", "?")
        lat            = s.get("lat", 0)
        lon            = s.get("lon", 0)
        score          = s.get("score", 0)
        population     = s.get("population", 0)
        road_desc      = s.get("road_desc", "No road data available")
        primary_len    = s.get("primary_length", 0) or 0
        secondary_len  = s.get("secondary_length", 0) or 0
        dist_primary   = s.get("dist_to_primary")
        dist_secondary = s.get("dist_to_secondary")
        road_density   = s.get("road_density", 0) or 0

        # Road quality
        if primary_len > 0 and secondary_len > 0:
            road_quality = "EXCELLENT — direct access to both primary and secondary roads"
            rq_style = styles["road_good"]

        elif primary_len > 0:
            road_quality = "GOOD — primary road passes directly through"
            rq_style = styles["road_good"]

        elif secondary_len > 0:
            dist_str = f"{dist_primary:.0f}m away" if dist_primary is not None else "unknown"
            road_quality = f"MODERATE — secondary road present, nearest primary road {dist_str}"
            rq_style = styles["body"]

        else:
            dist_str = f"{dist_primary:.0f}m" if dist_primary is not None else "unknown"
            road_quality = f"LIMITED — no direct road, nearest primary road {dist_str}"
            rq_style = styles["road_warn"]

        # Population label
        if population > 5000:
            pop_label = "HIGH density"
        elif population > 2000:
            pop_label = "MEDIUM density"
        else:
            pop_label = "LOW density"

        # Header
        loc_header = [[
            Paragraph(
                f"Location {rank} — {lat:.5f}, {lon:.5f} | Score: {score:.2f}",
                ParagraphStyle(
                    "loc_hdr",
                    fontSize=11,
                    fontName="Helvetica-Bold",
                    textColor=WHITE,
                )
            )
        ]]

        loc_hdr_table = Table(
            loc_header,
            colWidths=[170 * mm],
            hAlign="CENTER"
        )

        loc_hdr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))

        story.append(loc_hdr_table)

        detail_rows = [
            [
                Paragraph("<b>Population coverage</b>", styles["body"]),
                Paragraph(f"{population:,} ({pop_label} area)", styles["body"])
            ],

            [
                Paragraph("<b>Road access</b>", styles["body"]),
                Paragraph(road_desc, styles["body"])
            ],

            [
                Paragraph("<b>Road quality</b>", styles["body"]),
                Paragraph(road_quality, rq_style)
            ],

            [
                Paragraph("<b>Road density</b>", styles["body"]),
                Paragraph(f"{road_density:.0f} m/km²", styles["body"])
            ],
        ]

        detail_table = Table(
            detail_rows,
            colWidths=[80 * mm, 90 * mm],
            hAlign="CENTER"
        )

        detail_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, MID_GRAY),

            *[
                ("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY)
                for i in range(0, len(detail_rows), 2)
            ],
        ]))

        story.append(detail_table)
        story.append(Spacer(1, 2 * mm))

def _footer(story, styles):

    # story.append(Spacer(1, 1 * mm))

    story.append(HRFlowable(
        width="100%",
        thickness=0.5,
        color=MID_GRAY
    ))

    story.append(Spacer(1, 0.5 * mm))

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