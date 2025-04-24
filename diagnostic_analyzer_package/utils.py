import pkgutil
import openai
import textwrap
import os

# Pretty print function for CLI output
def pretty_print(message, type_="info"):
    """
    Pretty print a message to the console.
    
    Args:
        message (str): The message to print.
        type_ (str, optional): The type of message ('info', 'warning', 'error', 'success'). Defaults to "info".
    """
    if type_ == "info":
        print(f"\n[INFO] {message}")
    elif type_ == "warning":
        print(f"\n[WARNING] {message}")
    elif type_ == "error":
        print(f"\n[ERROR] {message}")
    elif type_ == "success":
        print(f"\n[SUCCESS] {message}")
    else:
        print(f"\n{message}")
    
# Function to read a file from the package data
def read_package_file(filename):
    """Reads a file from the package data."""
    data = pkgutil.get_data('diagnostic_analyzer_package', filename)
    if data:
        return data.decode('utf-8')
    else: 
        print(f"Error: File not found in package: {filename}")
        return None
    

# Function to process the output to a formatted string
def process_output_to_string(output):
    """Converts a dictionary output to a formatted string."""
    lines = []
    for key, value in output.items():
        lines.append(f"{key}:")
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                lines.append(f"  {sub_key}:")
                if isinstance(sub_value, list):
                    for item in sub_value:
                        lines.append(f"    {item}")
                else:
                    lines.append(f"    {sub_value}")
        elif isinstance(value, list):
            for item in value:
                lines.append(f"  {item}")
        else:
            lines.append(f"  {value}")
    return "\n".join(lines)

# Function to call the ChatGPT API
def call_chatgpt_api(prompt):

    # Set the OpenAI API key
    openai.api_key = os.getenv("OPENAI_API_KEY")

    try:
        response = openai.chat.completions.create(
            model="o3-mini",  # Or another suitable model
            messages=[
                {"role": "user", "content": prompt}
            ],
            # max_tokens=8500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"An error occurred: {e}")
        return e

def draw_wrapped_text(canvas, text, x, y, width, bottom_margin, height, top_margin, 
                     font="Helvetica", font_size=10, line_height=14, mono_font="Courier"):
    """
    Draws wrapped text on a PDF canvas and returns the new y position.
    
    Args:
        canvas: The ReportLab canvas object
        text (str): The text to draw
        x (float): Starting x position
        y (float): Starting y position
        width (float): Available width for text wrapping
        bottom_margin (float): Bottom margin of the page
        height (float): Page height
        top_margin (float): Top margin of the page
        font (str): Font name to use
        font_size (int): Font size
        line_height (int): Line height for text
        mono_font (str): Monospace font name for code blocks
        
    Returns:
        float: New y position after drawing text
    """
    # Calculate approximately how many characters fit on one line
    chars_per_line = int((width / (600/10)) * (10/font_size) * 10)
    
    # Process and wrap text
    lines = []
    for paragraph in text.split('\n'):
        if paragraph.strip() == '':
            lines.append('')  # Preserve empty lines
        else:
            # Check if this is a separator line (all same character)
            if paragraph and all(c == paragraph[0] for c in paragraph.strip()) and len(paragraph.strip()) > 10:
                # This is a separator line, keep it intact but trim if needed
                lines.append(paragraph[:chars_per_line])
            # Check if this is a bullet point
            elif paragraph.strip().startswith('•') or paragraph.strip().startswith('-'):
                # Preserve bullet points with proper wrapping
                indent = len(paragraph) - len(paragraph.lstrip())
                bullet = paragraph[:indent+2]  # bullet and following space
                rest = paragraph[indent+2:]
                wrapped = textwrap.wrap(rest, width=chars_per_line-indent-2)
                if wrapped:
                    lines.append(bullet + wrapped[0])
                    for wrap_line in wrapped[1:]:
                        lines.append(' ' * (indent+2) + wrap_line)
                else:
                    lines.append(bullet)
            # Regular text
            else:
                wrapped = textwrap.wrap(paragraph, width=chars_per_line)
                if wrapped:
                    lines.extend(wrapped)
                else:
                    lines.append('')  # Empty paragraph
    
    # Draw each line
    canvas.setFont(font, font_size)
    for line in lines:
        if y < bottom_margin:  # Check if we need a new page
            canvas.showPage()
            y = height - top_margin
            canvas.setFont(font, font_size)
            
        # Handle code blocks specially to avoid space character issues
        if font == mono_font:
            # Draw each non-space character with positioning
            pos_x = x
            space_width = canvas.stringWidth(' ', font, font_size)
            
            for char in line:
                if char == ' ':
                    # Just move the position by space width
                    pos_x += space_width
                else:
                    # Draw the character and advance position
                    canvas.drawString(pos_x, y, char)
                    pos_x += canvas.stringWidth(char, font, font_size)
        else:
            # Regular text drawn as usual
            canvas.drawString(x, y, line)
            
        y -= line_height
    
    return y