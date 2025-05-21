import re
import os
import json
import logging

from .utils import process_output_to_string, call_chatgpt_api

from .prompts import get_initial_thread_analysis_prompt, get_comprehensive_thread_analysis_prompt
from .thread_dump_processor import Analysis, ThreadStatus

# Configure logger
logger = logging.getLogger("diagnostic_analyzer")

# Function to analyze multiple thread dumps
def analyze_thread_dumps(thread_groups_config, in_memory_files):
    """
    Analyzes multiple thread dump files and combines the results into a single output file.

    Args:
        thread_groups_config (dict): Configuration for thread groups.
    """
    file_contents = []
    for i in range(1, 4):

        pattern = re.compile(rf"threaddump-{i}-\d+\.txt")
        matching_files = [f for f in in_memory_files.keys() if pattern.match(f)]

        # Skip this iteration if no matching files are found
        if not matching_files:
            logger.warning(f"No matching thread dump file found for pattern threaddump-{i}-\\d+\\.txt")
            continue

        thread_dump_filename = matching_files[0]

        # Get file content directly from in_memory_files
        file_content = in_memory_files[thread_dump_filename]
        
        # Handle different types of file content
        if hasattr(file_content, 'read'):
            # If it's a file-like object (BytesIO, etc.)
            file_content.seek(0)  # Ensure we're at the start of the file
            if hasattr(file_content, 'getvalue'):
                # BytesIO object
                thread_dump_text = file_content.getvalue()
            else:
                # Other file-like object
                thread_dump_text = file_content.read()
                file_content.seek(0)  # Reset position after reading
                
            # Convert bytes to string if needed
            if isinstance(thread_dump_text, bytes):
                thread_dump_text = thread_dump_text.decode('utf-8', errors='ignore')
        else:
            # If it's already a string or bytes
            thread_dump_text = file_content
            if isinstance(thread_dump_text, bytes):
                thread_dump_text = thread_dump_text.decode('utf-8', errors='ignore')

        analysis_id = i
        analysis_name = f"Thread Dump Analysis {i}"
        analysis_config = {}

        analysis = Analysis(analysis_id, analysis_name, analysis_config, thread_groups_config)
        analysis.analyze(thread_dump_text)

        output = {
            "deadlocks": analysis.deadlockStatus,
            "threadsByState": {},
            "threadsByPool": {}
        }

        thread_frames_var_name = f"thread_frames_{i}"
        globals()[thread_frames_var_name] = {thread.name: thread.frames for thread in analysis.threads}

        for pool_name, threads in analysis.threadsByPool.items():
            output["threadsByPool"][pool_name] = [thread.name for thread in threads]

        for status in ThreadStatus.ALL:
            if status in analysis.threadsByStatus:
                output["threadsByState"][status] = [{
                    "name": thread.name,
                    "threadState": thread.threadState,
                    "wantNotificationOn": thread.wantNotificationOn,
                    "classicalLockHeld": thread.classicalLockHeld,
                    "tid": thread.tid,
                    "locksHeld": thread.locksHeld,
                } for thread in analysis.threadsByStatus[status]]

        file_contents.append(process_output_to_string(output))

    combined_content = "\n\n".join(file_contents)

    return combined_content

# Function to analyze thread dumps and extract problematic threads
def analyze_thread_dumps_and_extract_problems(thread_groups_config, in_memory_files, customer_problem):
    """
    Analyzes thread dumps, identifies problematic threads, and performs initial analysis.
    
    Args:
        thread_groups_config (dict): Configuration for thread groups.
        folder_path (str): Path to the folder containing thread dumps.
        customer_problem (str): Description of the customer's problem.
        
    Returns:
        tuple: A tuple containing (initial_report, problem_threads)
    """
    logger.info("Analyzing thread dumps and extracting problematic threads...")
    combined_content = analyze_thread_dumps(thread_groups_config, in_memory_files)
    
    if not combined_content:
        return "No thread dump content could be analyzed.", []

    try:
        # Call the API for initial analysis
        initial_prompt = get_initial_thread_analysis_prompt(customer_problem, combined_content, thread_groups_config)
        initial_response = call_chatgpt_api(initial_prompt)
        if "context_length_exceeded" in initial_response:
            logger.warning("Context length exceeded. Trying with a smaller context.")
            short_initial_prompt = get_initial_thread_analysis_prompt(customer_problem, combined_content[:600000])
            initial_response = call_chatgpt_api(short_initial_prompt)
            
        problem_threads = extract_problem_threads(initial_response)
        
        return initial_response, problem_threads
        
    except Exception as e:
        logger.error(f"Error in thread dump analysis: {str(e)}")
        
# Extract thread names from the initial response
def extract_problem_threads(initial_response):
    """
    Extracts thread names from any Python-style list found in the response.

    Args:
        initial_response: The initial report from the ChatGPT API.

    Returns:
        A list of thread names, or an empty list if none are found.
    """
    try:
        # Find any Python-style list in the response
        match = re.search(r"\[(.*?)\]", initial_response, re.DOTALL)
        if match:
            list_string = "[" + match.group(1) + "]"
            # Parse the list using json.loads
            problem_threads = json.loads(list_string)
            return problem_threads
        else:
            return []  # Return an empty list if no list is found
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from response.")
        return []
    except Exception as e:
        logger.error(f"An error occurred during thread extraction: {e}")
        return []
    
# Function to fetch stack traces from thread frames when thread name is provided
def get_stack_trace(thread_name):
    try:
        for i in range(1, 4):
            thread_frames_var_name = f"thread_frames_{i}"
            thread_frames = globals()[thread_frames_var_name]
            if thread_name in thread_frames:
                return thread_frames[thread_name]
    except Exception as error:
        logger.error(f"Failed to get stack trace for {thread_name}: {error}")


# Function to get comprehensive thread analysis using stack traces
def get_comprehensive_thread_analysis(initial_response, problem_threads, customer_problem, log_content):
    """
    Gets a comprehensive analysis of problematic threads using their stack traces.
    
    Args:
        initial_response (str): The initial thread dump analysis report.
        problem_threads (list): List of problematic thread names.
        customer_problem (str): Description of the customer's problem.
        log_content (str): Content of the log file.
        
    Returns:
        str: Comprehensive thread analysis report.
    """
    logger.info("Performing comprehensive thread analysis...")
    
    if not problem_threads:
        logger.info("No problematic threads identified, skipping comprehensive analysis")
        return "No problematic threads identified for comprehensive analysis."
    
    # Collect stack traces for each problematic thread
    thread_stack_traces = {}
    for thread_name in problem_threads:
        stack_trace = get_stack_trace(thread_name)
        thread_stack_traces[thread_name] = stack_trace
    
    comprehensive_prompt = get_comprehensive_thread_analysis_prompt(customer_problem, initial_response, log_content, thread_stack_traces)
    
    try:
        comprehensive_analysis = call_chatgpt_api(comprehensive_prompt)
        return comprehensive_analysis
        
    except Exception as e:
        error_message = f"Error in comprehensive thread analysis: {str(e)}"
        logger.error(error_message)
        return error_message

