import time

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from .utils import draw_wrapped_text

# def write_analysis_report(content, report_type, filename=None):
#     """
#     Writes an analysis report as a PDF.
    
#     Args:
#         content (str): The content of the report.
#         report_type (str): Type of report (e.g., 'log_analysis', 'class_analysis', 'thread_analysis').
#         filename (str, optional): Custom filename. If None, a default name will be generated based on report_type.
        
#     Returns:
#         content (str): content for further processing
#     """
#     try:
#         # Generate default filename if not provided
#         if not filename:
#             base_filename = f"{report_type.lower().replace(' ', '_')}_report"
#             filename = f"{base_filename}.pdf"
        
#         # Make sure the filename ends with .pdf
#         if not filename.lower().endswith('.pdf'):
#             filename += '.pdf'
            
#         print(f"\n[INFO] Generating {report_type} PDF report...")
        
#         # Set up the canvas and PDF
#         c = canvas.Canvas(filename, pagesize=letter)
#         width, height = letter
        
#         # Set margins
#         left_margin = 1 * inch
#         right_margin = 1 * inch
#         top_margin = 1 * inch
#         bottom_margin = 1 * inch
        
#         # Calculate text width
#         text_width = width - left_margin - right_margin
        
#         # Set up fonts
#         title_font = "Helvetica-Bold"
#         normal_font = "Helvetica"
#         mono_font = "Courier"
        
#         # Starting y position (from top of page)
#         y = height - top_margin
        
#         # Report title
#         report_title = f"{report_type.title()} Report"
#         c.setFont(title_font, 18)
#         title_width = c.stringWidth(report_title, title_font, 18)
#         c.drawString((width - title_width) / 2, y, report_title)
#         y -= 30
        
#         # Report content - using monospace font for analysis results
#         y = draw_wrapped_text(c, content, left_margin, y, text_width, 
#                              bottom_margin, height, top_margin,
#                              font=mono_font, font_size=9, line_height=11)
        
#         # Generated timestamp
#         y -= 20
#         timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
#         c.setFont(normal_font, 10)
#         c.drawString(left_margin, bottom_margin / 2, f"Generated on: {timestamp}")
        
#         # Save PDF
#         c.save()
        
#         # Also save a text version for backward compatibility/extraction
#         text_filename = os.path.splitext(filename)[0] + '.txt'
#         with open(text_filename, 'w') as text_file:
#             text_file.write(content)
        
#         print(f"[INFO] {report_type.title()} report generated: {filename}")
#         print(f"[INFO] Text version saved to: {text_filename}")
        
#         return content
        
#     except Exception as e:
#         error_message = f"[ERROR] Error generating {report_type} PDF report: {str(e)}"
#         print(error_message)
#         return None, content

def write_final_report(customer_problem, log_analysis, comprehensive_analysis, class_analysis=None, final_report=None):
    """
    Writes the final consolidated report as a PDF.
    """
    print("\n[INFO] Generating final PDF report...")
    
    # Set up the canvas and PDF
    report_filename = 'final_diagnostic_report.pdf'
    c = canvas.Canvas(report_filename, pagesize=letter)
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
    
    # Save PDF
    c.save()
    
    print(f"[INFO] Final PDF report generated: {report_filename}")
    return report_filename
