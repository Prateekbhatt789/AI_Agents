from fpdf import FPDF
import os

os.makedirs("reports", exist_ok=True)

def generate_pdf(location: str, lat: float, lon: float, radius_km: float, summary: dict) -> str:
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_fill_color(30, 80, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "GIS Site Analysis Report", fill=True, ln=True, align="C")
    pdf.ln(5)

    # Location details
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 80, 160)
    pdf.cell(0, 10, "Location Details", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, f"Location  : {location}", ln=True)
    pdf.cell(0, 8, f"Coordinates: {lat:.4f}, {lon:.4f}", ln=True)
    pdf.cell(0, 8, f"Radius    : {radius_km} km", ln=True)
    pdf.ln(5)

    # POI table
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 80, 160)
    pdf.cell(0, 10, "Points of Interest", ln=True)

    pdf.set_fill_color(30, 80, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(120, 9, "Category", border=1, fill=True)
    pdf.cell(60,  9, "Count",    border=1, fill=True, ln=True)

    rows = [
        ("Hospitals & Clinics", summary.get("human_hospitals", 0)),
        ("Vet Hospitals",       summary.get("vet_hospitals", 0)),
        ("Bus Stops",           summary.get("bus_stops", 0)),
        ("Fuel Stations",       summary.get("fuel_stations", 0)),
        ("Schools",             summary.get("schools", 0)),
        ("Restaurants",         summary.get("restaurants", 0)),
        ("Pharmacies",          summary.get("pharmacies", 0)),
        ("Buildings",           summary.get("buildings", 0)),
    ]

    pdf.set_font("Helvetica", "", 11)
    for i, (cat, count) in enumerate(rows):
        pdf.set_fill_color(240, 245, 255) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(120, 9, cat,        border=1, fill=True)
        pdf.cell(60,  9, str(count), border=1, fill=True, ln=True)

    path = "reports/site_report.pdf"
    pdf.output(path)
    return path