import os
import requests
import base64
import ast
import re
import logging

from .utils import call_chatgpt_api
from .prompts import get_log_analysis_prompt, get_class_analysis_prompt

logger = logging.getLogger("diagnostic_analyzer")

def get_log_content(in_memory_files):
    """
    Retrieves the content of the log.txt file from in-memory files.

    Args:
        in_memory_files (dict): Dictionary of {filename: file_content} for in-memory files.
            Each file_content should be a BytesIO object or a bytes/string content.

    Returns:
        str: The content of the log.txt file, or None if not found.
    """
    # Check if log.txt exists in the in_memory_files dictionary
    if 'log.txt' not in in_memory_files:
        logger.error("Error: log.txt not found in uploaded files")
        return None
    
    try:
        # Get the content from the dictionary
        file_content = in_memory_files['log.txt']
        
        # Handle different types of file content
        if hasattr(file_content, 'read'):
            # If it's a file-like object (BytesIO, etc.)
            file_content.seek(0)  # Ensure we're at the start of the file
            
            if hasattr(file_content, 'getvalue'):
                # BytesIO object
                log_content = file_content.getvalue()
            else:
                # Other file-like object
                log_content = file_content.read()
                file_content.seek(0)  # Reset position after reading
                
            # Convert bytes to string if needed
            if isinstance(log_content, bytes):
                log_content = log_content.decode('utf-8', errors='ignore')
        else:
            # If it's already a string or bytes
            log_content = file_content
            if isinstance(log_content, bytes):
                log_content = log_content.decode('utf-8', errors='ignore')
                
        return log_content
        
    except Exception as e:
        logger.error(f"Error processing log.txt: {e}")
        return None
    
# Function to analyze error logs
def analyze_error_log(log_content, customer_problem):
    """
    Analyzes error logs to identify patterns and potential issues.
    
    Args:
        log_content (str): Content of the log file.
        customer_problem (str): Description of the customer's problem.
        
    Returns:
        tuple: A tuple containing (return log_analysis, suspected_classes, error_message)
    """
    
    logger.info("Analyzing error logs...")
    
    if not log_content:
        logger.warning("[WARNING] No log content available for analysis")
        return "No log content available for analysis.", []

    sus_classes = [
    {"package": "org.apache.synapse.commons.json", "class": "JsonUtil", "issue_line": 123},
    {"package": "org.apache.synapse.mediators.builtin", "class": "LogMediator", "issue_line": 456},]

    log_analysis_prompt = get_log_analysis_prompt(customer_problem, log_content, sus_classes)
    
    try:
        log_analysis = call_chatgpt_api(log_analysis_prompt)
        
        # # Generate PDF report and also save text version
        # log_analysis = write_analysis_report(
        #     log_analysis, 
        #     'Log Analysis', 
        #     'log_analysis_report.pdf'
        # )
        
        # Extract suspected classes from the response
        suspected_classes = extract_suspected_classes(log_analysis)
        error_message = extract_error_message(log_analysis)        
        return log_analysis, suspected_classes, error_message
        
    except Exception as e:
        logger.error(f"[ERROR] Error in log analysis: {str(e)}")
        return error_message, []

# Function to extract suspected classes from log analysis
def extract_suspected_classes(log_analysis):
    """
    Extracts suspected class names from the log analysis response.
    
    Args:
        log_analysis (str): The log analysis report from the ChatGPT API.
        
    Returns:
        list: A list of dictionaries with "package" and "class" keys, or an empty list if none are found.
    """
    try:
        # Match the line starting with SUSPECTED_CLASSES followed by a Python list
        match = re.search(r"SUSPECTED_CLASSES:\s*(\[.*?\])", log_analysis, re.DOTALL)
        if match:
            suspected_classes_str = match.group(1)
            suspected_classes = ast.literal_eval(suspected_classes_str)
            if isinstance(suspected_classes, list):
                return suspected_classes
    except Exception as e:
        logger.error(f"Error while extracting suspected classes: {e}")

    return []

def extract_error_message(log_analysis):
    """
    Extracts error messages from the log analysis response.
    
    Args:
        log_analysis (str): The log analysis report from the ChatGPT API.
        
    Returns:
        str: The error message, or an empty string if none are found.
    """
    try:
        # Match the line starting with ERROR_MESSAGE followed by a Python string
        match = re.search(r"ERROR_MESSAGE:\s*(.*)", log_analysis, re.DOTALL)
        if match:
            error_message = match.group(1).strip()
            return error_message
    except Exception as e:
        logger.error(f"Error while extracting error message: {e}")

    return ""
    
# Function to fetch and analyze class files
def fetch_and_analyze_files(suspected_classes, customer_problem, error_message_text, log_analysis):
    """
    Fetches the specified class files from GitHub and analyzes them.
    
    Args:
        class_names (list): List of class names to analyze.
        customer_problem (str): Description of the customer's problem.
        
    Returns:
        str: Report of the class file analysis.
    """
        
    if not suspected_classes:
        return "No class files specified for analysis."
    
    # Simulated class file content for demonstration
    class_files_content = {}
    
    for sus_class in suspected_classes:
        filename = sus_class["class"]
        package_name = sus_class["package"]
        line_number = sus_class["issue_line"]
        file_path = get_file_path(filename, package_name)
        file_content = fetch_file_content(file_path)
        file_content_with_line_number = embed_line_number(file_content, line_number)

        class_files_content[filename] = f"// Content in {filename}\n// {file_content_with_line_number} \n// Line number with the issue: {line_number}\n"
    
    class_analysis_prompt = get_class_analysis_prompt(customer_problem, class_files_content, error_message_text, log_analysis)
    
    try:
        class_analysis = call_chatgpt_api(class_analysis_prompt)
        
        # # Generate PDF report and also save text version
        # class_analysis = write_analysis_report(
        #     class_analysis, 
        #     'Class Analysis', 
        #     'class_analysis_report.pdf'
        # )
        
        return class_analysis
        
    except Exception as e:
        error_message = f"[ERROR] Error in class analysis: {str(e)}"
        logger.error(error_message)
        return error_message
    
# Function to embed line number in the file content
def embed_line_number(file_content, line_number):
    """
    Embeds the line number in the file content.
    
    Args:
        file_content (str): The content of the file.
        line_number (int): The line number to embed.
        
    Returns:
        str: The file content with the line number embedded.
    """
    lines = file_content.split('\n')
    if 0 < line_number <= len(lines):
        lines[line_number - 1] = f"// {lines[line_number - 1]} this is the line {line_number} with the issue"
    return '\n'.join(lines)
    
def get_file_path(filename: str, package_name: str) -> str:
    owner = "WSO2"
    token = os.getenv("GITHUB_API_KEY")
    path = package_name.replace('.', '/')

    try:
        # Search for file paths
        file_urls = search_file_paths(owner, filename, token)
        for file_url in file_urls:
            if path in file_url:
                return file_url
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error: {e}")

# Function to search for file paths by file name
def search_file_paths(owner, filename, token):
    query = f"org:{owner} filename:{filename}.java"
    url = f"https://api.github.com/search/code?q={query}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    search_results = response.json()
    
    return [item['url'] for item in search_results['items']]

def fetch_file_content(url: str) -> str:
    GITHUB_TOKEN = os.getenv("GITHUB_API_KEY")
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # The content is base64 encoded, so we need to decode it
        content = response.json().get('content', '')
        decoded_content = base64.b64decode(content).decode('utf-8')
        return decoded_content
    else:
        raise Exception(f'Failed to retrieve file: {response.json().get("message")}')
    