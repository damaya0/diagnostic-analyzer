import time
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import logging

from .utils import draw_wrapped_text

# Configure logger
logger = logging.getLogger("diagnostic_analyzer")

def write_final_report(customer_problem, log_analysis, comprehensive_analysis, class_analysis=None, final_report=None):
    """
    Writes the final consolidated report as a PDF and returns it as a BytesIO object (in-memory).
    """
    logger.info("Generating final PDF report (in-memory)...")
    
    # Use an in-memory bytes buffer
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Set margins
    left_margin = 1 * inch
    right_margin = 1 * inch
    top_margin = 1 * inch
    bottom_margin = 1 * inch
    
    # Calculate text width
    text_width = width - left_margin - right_margin
    
    # Set up fonts
    title_font = "Helvetica-Bold"
    heading_font = "Helvetica-Bold"
    normal_font = "Helvetica"
    mono_font = "Courier"
    
    # Starting y position (from top of page)
    y = height - top_margin
    
    # Title
    c.setFont(title_font, 24)
    title = "Diagnostic Analysis Report"
    title_width = c.stringWidth(title, title_font, 24)
    c.drawString((width - title_width) / 2, y, title)
    y -= 40
    
    # Customer Problem
    c.setFont(heading_font, 18)
    c.drawString(left_margin, y, "Customer Problem")
    y -= 30
    y = draw_wrapped_text(c, customer_problem, left_margin, y, text_width, 
                         bottom_margin, height, top_margin)
    y -= 20

    # Log Analysis
    c.setFont(heading_font, 14)
    c.drawString(left_margin, y, "Log Analysis")
    y -= 20
    y = draw_wrapped_text(c, log_analysis, left_margin, y, text_width,
                         bottom_margin, height, top_margin, 
                         font=mono_font, font_size=9, line_height=11)
    
    # Check if we need a new page
    if y < height / 2:
        c.showPage()
        y = height - top_margin
    
    # Comprehensive Thread Analysis
    c.setFont(heading_font, 14)
    c.drawString(left_margin, y, "Comprehensive Thread Analysis")
    y -= 20
    y = draw_wrapped_text(c, comprehensive_analysis, left_margin, y, text_width,
                         bottom_margin, height, top_margin, 
                         font=mono_font, font_size=9, line_height=11)
    y -= 20
    
    # Class Analysis if available
    if class_analysis:
        # Check if we need a new page
        if y < height / 2:
            c.showPage()
            y = height - top_margin
        
        c.setFont(heading_font, 14)
        c.drawString(left_margin, y, "Class Files Analysis")
        y -= 20
        y = draw_wrapped_text(c, class_analysis, left_margin, y, text_width,
                             bottom_margin, height, top_margin, 
                             font=mono_font, font_size=9, line_height=11)
        y -= 20
    
    # Conclusions
    # Check if we need a new page
    if y < height / 3:
        c.showPage()
        y = height - top_margin
    
    c.setFont(heading_font, 14)
    c.drawString(left_margin, y, "Conclusions and Recommendations")
    y -= 20
    y = draw_wrapped_text(c, final_report, left_margin, y, text_width,
                             bottom_margin, height, top_margin, 
                             font=mono_font, font_size=9, line_height=11)
    y -= 20
    
    # Generated timestamp
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    c.setFont(normal_font, 10)
    c.drawString(left_margin, bottom_margin / 2, f"Generated on: {timestamp}")
    
    # Finalize the PDF and rewind the buffer
    c.save()
    buffer.seek(0)  # Move to the beginning so send_file works properly

    logger.info("Final PDF report generated in memory.")
    return buffer
