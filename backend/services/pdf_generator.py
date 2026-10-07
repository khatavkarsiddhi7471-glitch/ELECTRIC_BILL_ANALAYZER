"""
PDF report generation service using ReportLab and Matplotlib.
Generates comprehensive analysis reports with summary metrics, slab breakdown tables, trend charts, appliance rankings, and energy saving tips.
"""

import os
import io
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable, KeepTogether
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def generate_pdf_report(user, bill, bills_history, appliances, prediction, tips):
    """
    Generate downloadable PDF report as a BytesIO stream.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#64748B')
    )
    
    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    story = []
    
    # Header Banner
    header_data = [
        [
            Paragraph("⚡ <b>Smart Electricity Bill Analyzer</b><br/><font color='#64748B' size='8'>Monthly Energy Analytics & Cost Optimization Report</font>", title_style),
            Paragraph(f"<b>Bill Month:</b> {bill.get('month', 'N/A')}<br/><b>Generated:</b> {datetime.now().strftime('%d %b %Y')}", ParagraphStyle('HeadRight', parent=body_style, alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 180])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceBefore=4, spaceAfter=12))
    
    # User Profile & Overview Grid
    user_name = user.get('name', 'Resident')
    consumer_no = user.get('consumer_number', 'Not Specified')
    total_amt = f"₹{bill.get('calculated_total', 0):,.2f}"
    units_consumed = f"{bill.get('units', 0):,.0f} kWh"
    avg_rate = f"₹{bill.get('calculated_total', 0) / max(1, bill.get('units', 1)):.2f}/kWh"
    
    kpi_data = [
        [
            Paragraph(f"<b>Consumer:</b> {user_name}<br/><b>Consumer ID:</b> {consumer_no}", body_style),
            Paragraph(f"<b>Total Units Consumed:</b><br/><font size='12' color='#2563EB'><b>{units_consumed}</b></font>", body_style),
            Paragraph(f"<b>Total Bill Amount:</b><br/><font size='12' color='#059669'><b>{total_amt}</b></font>", body_style),
            Paragraph(f"<b>Average Cost/Unit:</b><br/><font size='12' color='#D97706'><b>{avg_rate}</b></font>", body_style)
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[130, 130, 130, 130])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 10))
    
    # Slab-wise Breakdown Table
    story.append(Paragraph("📊 Slab-wise Tariff Breakdown", h2_style))
    breakdown = bill.get("breakdown", {})
    slab_lines = breakdown.get("slab_charges", [])
    
    table_rows = [["Slab Range", "Units Billed", "Rate (₹/Unit)", "Amount (₹)"]]
    for line in slab_lines:
        table_rows.append([
            f"{line.get('range', '')} Units",
            f"{line.get('units', 0):,.1f}",
            f"₹{line.get('rate', 0):.2f}",
            f"₹{line.get('amount', 0):,.2f}"
        ])
    
    # Add summary rows
    table_rows.append(["Energy Charges", "", "", f"₹{breakdown.get('energy_charge', 0):,.2f}"])
    table_rows.append(["Fixed / Demand Charges", "", "", f"₹{breakdown.get('fixed_charge', 0):,.2f}"])
    table_rows.append(["Electricity Duty & Taxes", "", "", f"₹{breakdown.get('duty', 0):,.2f}"])
    if breakdown.get('other_charges', 0) > 0:
        table_rows.append(["Other Surcharges", "", "", f"₹{breakdown.get('other_charges', 0):,.2f}"])
    if breakdown.get('rebate', 0) > 0:
        table_rows.append(["Rebate / Subsidy", "", "", f"-₹{breakdown.get('rebate', 0):,.2f}"])
    table_rows.append(["Total Calculated Payable", "", "", f"₹{bill.get('calculated_total', 0):,.2f}"])
    
    t_breakdown = Table(table_rows, colWidths=[200, 100, 100, 120])
    num_slabs = len(slab_lines)
    t_breakdown.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_breakdown)
    story.append(Spacer(1, 10))
    
    # Matplotlib Trend Chart
    if bills_history and len(bills_history) >= 2:
        story.append(Paragraph("📈 Historical Usage & Cost Trend", h2_style))
        chart_img_path = _generate_matplotlib_chart(bills_history)
        if chart_img_path and os.path.exists(chart_img_path):
            story.append(RLImage(chart_img_path, width=520, height=160))
            story.append(Spacer(1, 10))

    # Next Month Prediction & Appliance Section
    row_pred_app = []
    
    pred_text = "<b>Next Month Forecast:</b><br/>"
    if prediction and prediction.get("status") == "success":
        pred_text += f"• <b>Predicted Usage:</b> {prediction.get('predicted_units', 0):,.0f} kWh<br/>"
        pred_text += f"• <b>Estimated Bill:</b> ₹{prediction.get('predicted_amount', 0):,.2f}<br/>"
        pred_text += f"• <b>Method:</b> {prediction.get('method', 'Trend Model')}<br/>"
        c_range = prediction.get("confidence_range", {})
        if c_range and "amount_range" in c_range:
            pred_text += f"• <b>Expected Range:</b> ₹{c_range['amount_range'][0]:,.0f} - ₹{c_range['amount_range'][1]:,.0f}"
    else:
        pred_text += "Add 3+ billing cycles to unlock ML forecasting."
        
    app_text = "<b>Top Consuming Appliances:</b><br/>"
    if appliances:
        sorted_apps = sorted(appliances, key=lambda x: x.get("monthly_kwh", 0), reverse=True)[:3]
        for a in sorted_apps:
            app_text += f"• <b>{a.get('name')}:</b> {a.get('monthly_kwh', 0):.0f} kWh (~₹{a.get('estimated_cost', 0):.0f})<br/>"
    else:
        app_text += "No appliances tracked yet."
        
    dual_data = [[
        Paragraph(pred_text, body_style),
        Paragraph(app_text, body_style)
    ]]
    t_dual = Table(dual_data, colWidths=[260, 260])
    t_dual.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_dual)
    story.append(Spacer(1, 10))
    
    # Energy Saving Tips Section
    if tips:
        story.append(Paragraph("💡 Personalized Energy Saving Actions", h2_style))
        for tip in tips[:3]:
            tip_html = f"<b>{tip.get('title')}</b> ({tip.get('tag', 'Tip')}) — <font color='#059669'><b>Est. Savings: ₹{tip.get('estimated_monthly_savings_inr', 0)}/mo</b></font><br/>{tip.get('tip')}"
            story.append(Paragraph(f"• {tip_html}", body_style))
            story.append(Spacer(1, 4))
            
    doc.build(story)
    buffer.seek(0)
    return buffer

def _generate_matplotlib_chart(bills):
    """Render historical line chart into temporary PNG for ReportLab embedding"""
    try:
        months = [b.get("month", "") for b in bills][-6:]
        units = [float(b.get("units", 0)) for b in bills][-6:]
        amounts = [float(b.get("calculated_total", 0)) for b in bills][-6:]
        
        fig, ax1 = plt.subplots(figsize=(8, 2.4), dpi=150)
        
        color1 = '#2563eb'
        ax1.set_xlabel('Billing Month', fontsize=8)
        ax1.set_ylabel('Units (kWh)', color=color1, fontsize=8)
        ax1.plot(months, units, color=color1, marker='o', linewidth=2, label='Units (kWh)')
        ax1.tick_params(axis='y', labelcolor=color1, labelsize=7)
        ax1.tick_params(axis='x', labelsize=7)
        ax1.grid(True, linestyle='--', alpha=0.3)
        
        ax2 = ax1.twinx()
        color2 = '#059669'
        ax2.set_ylabel('Bill Amount (₹)', color=color2, fontsize=8)
        ax2.plot(months, amounts, color=color2, marker='s', linestyle='--', linewidth=2, label='Amount (₹)')
        ax2.tick_params(axis='y', labelcolor=color2, labelsize=7)
        
        plt.title('Consumption & Cost Trend (Recent Months)', fontsize=9, fontweight='bold', pad=8)
        plt.tight_layout()
        
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(tmp.name, format='png', bbox_inches='tight')
        plt.close(fig)
        return tmp.name
    except Exception as e:
        print(f"Chart generation note: {e}")
        return None
