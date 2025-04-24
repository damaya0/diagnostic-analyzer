import re
import os
import json

from .utils import process_output_to_string, call_chatgpt_api
from .prompts import get_initial_thread_analysis_prompt, get_comprehensive_thread_analysis_prompt
from .report import write_analysis_report
from .thread_dump_processor import Analysis, ThreadStatus

# Function to analyze multiple thread dumps
def analyze_thread_dumps(thread_groups_config, folder_path):
    """
    Analyzes multiple thread dump files and combines the results into a single output file.

    Args:
        thread_groups_config (dict): Configuration for thread groups.
    """
    file_contents = []
    for i in range(1, 4):

        pattern = re.compile(rf"threaddump-{i}-\d+\.txt")
        matching_files = [f for f in os.listdir(folder_path) if pattern.match(f)]
        
        if not matching_files:
            print(f"No thread dump files found matching pattern threaddump-{i}-*.txt")
            continue
            
        thread_dump_filename = matching_files[0]
        print(thread_dump_filename)

        thread_dump_filepath = os.path.join(folder_path, thread_dump_filename) #create the full file path.

        try:
            with open(thread_dump_filepath, 'r', encoding='utf-8') as f:
                thread_dump_text = f.read()
        except Exception as error:
            print(f"Failed to read {thread_dump_filename}: {error}")
            continue

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

    with open('combined_thread_content.txt', 'w') as file:
        file.write(combined_content)

    return combined_content

# Function to analyze thread dumps and extract problematic threads
def analyze_thread_dumps_and_extract_problems(thread_groups_config, folder_path, customer_problem):
    """
    Analyzes thread dumps, identifies problematic threads, and performs initial analysis.
    
    Args:
        thread_groups_config (dict): Configuration for thread groups.
        folder_path (str): Path to the folder containing thread dumps.
        customer_problem (str): Description of the customer's problem.
        
    Returns:
        tuple: A tuple containing (initial_report, problem_threads)
    """
    combined_content = analyze_thread_dumps(thread_groups_config, folder_path)
    
    if not combined_content:
        return "No thread dump content could be analyzed.", []

    try:
        # Call the API for initial analysis
        print("\n[INFO] Performing initial thread dump analysis...")
        initial_prompt = get_initial_thread_analysis_prompt(customer_problem, combined_content)
        initial_response = call_chatgpt_api(initial_prompt)
        if "context_length_exceeded" in initial_response:
            print("Context length exceeded. Trying with a smaller context.")
            short_initial_prompt = get_initial_thread_analysis_prompt(customer_problem, combined_content[:600000])
            initial_response = call_chatgpt_api(short_initial_prompt)

        # Save the initial report
        # Save the initial report using write_analysis_report
        pdf_path, initial_response = write_analysis_report(
            initial_response, 
            'Initial Thread Dump Analysis', 
            'initial_thread_dump_analysis.pdf'
        )
        print(f"[INFO] Initial thread dump analysis completed and saved to '{pdf_path}'")
        
        # Extract problem threads from the response
        problem_threads = extract_problem_threads(initial_response)
        print(f"[INFO] Identified {len(problem_threads)} problematic threads: {problem_threads}")
        
        return initial_response, problem_threads
        
    except Exception as e:
        error_message = f"[ERROR] Error in thread dump analysis: {str(e)}"
        print(error_message)
        return error_message, []

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
        print("Error decoding JSON from response.")
        return []
    except Exception as e:
        print(f"An error occurred during thread extraction: {e}")
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
        print(f"Failed to get stack trace for {thread_name}: {error}")


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
    print("\n[INFO] Performing comprehensive thread analysis...")
    
    if not problem_threads:
        print("[INFO] No problematic threads identified, skipping comprehensive analysis")
        return "No problematic threads identified for comprehensive analysis."
    
    # Collect stack traces for each problematic thread
    thread_stack_traces = {}
    for thread_name in problem_threads:
        print(f"[INFO] Extracting stack trace for thread: {thread_name}")
        stack_trace = get_stack_trace(thread_name)
        thread_stack_traces[thread_name] = stack_trace
    
    comprehensive_prompt = get_comprehensive_thread_analysis_prompt(customer_problem, initial_response, log_content, thread_stack_traces)
    
    try:
        comprehensive_analysis = call_chatgpt_api(comprehensive_prompt)
        
        # Generate PDF report and also save text version
        pdf_path, comprehensive_analysis = write_analysis_report(
            comprehensive_analysis, 
            'Thread Analysis', 
            'comprehensive_thread_analysis.pdf'
        )
        
        return comprehensive_analysis
        
    except Exception as e:
        error_message = f"[ERROR] Error in comprehensive thread analysis: {str(e)}"
        print(error_message)
        return error_message
    
