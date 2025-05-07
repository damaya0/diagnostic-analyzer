import json

def get_initial_thread_analysis_prompt(customer_problem, combined_content):

    initial_prompt = f"""
    # Thread Dump Analysis Request
    
    ## Customer Problem
    {customer_problem}
    
    ## Thread Dumps
    The following contains thread dumps taken when the issue occurred:
    
    {combined_content}
    
    ## Analysis Request
    1. Analyze these thread dumps to identify potential issues
    2. Look for patterns across the dumps such as:
       - Threads in BLOCKED state
       - Deadlocks or potential deadlocks
       - High CPU threads
       - Threads waiting for resources
       - Any unusual thread states
    3. Provide a summary of your findings
    4. At the end of your report, list the specific thread names that require further detailed analysis in this format:
       THREADS_FOR_ANALYSIS: ["thread_name_1", "thread_name_2", ...]
       limit the number of threads to 5.
    5. If there are no threads with potential issues, keep the list empty.
       THREADS_FOR_ANALYSIS: []

    ## Important Note
    Note that your response will be directly written into a pdf report, so please ensure to fromat your response accordingly. **Do not leave indentation spaces in the response**. Start all sentences at the begining of a newline.
    """
    return initial_prompt

def get_comprehensive_thread_analysis_prompt(customer_problem, initial_response, log_content, thread_stack_traces):
    # Create a comprehensive analysis prompt with thread stack traces
    comprehensive_prompt = f"""
    # Comprehensive Thread Analysis Request
    
    ## Customer Problem
    {customer_problem}
    
    ## Initial Analysis Summary
    {initial_response}
    
    ## System Logs
    {log_content if log_content else "No log content available."}
    
    ## Problematic Threads and Their Stack Traces
    {json.dumps(thread_stack_traces, indent=2)}
    
    ## Analysis Request
    1. For each problematic thread:
        - Analyze its stack trace in detail
        - Explain what the thread is doing and why it might be problematic
        - Identify specific issues (e.g., locks, resource contention, infinite loops)
    2. Analyze how these issues relate to the system logs
    3. Provide an overall diagnosis of the root cause
    4. Suggest specific solutions to address the identified issues

    ## Important Note
    Note that your response will be directly written into a pdf report, so please ensure to fromat your response accordingly. **Do not leave indentation spaces in the response**. Start all sentences at the begining of a newline.
    """
    return comprehensive_prompt

def get_log_analysis_prompt(customer_problem, log_content, sus_classes):
    # Create a prompt for log analysis
    log_analysis_prompt = f"""
    # You are a software engineer at wso2 and you are analyzing error logs related to the following customer problem to identify potential issues.
    
    ## Customer Problem
    {customer_problem}
    
    ## System Logs
    The following contains system logs around the time the issue occurred:
    
    {log_content}
    
    ## Analysis Request
    1. Analyze these logs to identify patterns, errors, and warnings
    2. Look for:
       - Exception messages and stack traces
       - Error patterns
       - Suspicious timing of events
       - Component failures
    3. Provide a summary of your findings
    4. Decide what classes you would analyze further to get a better idea about the issue, give a list of dictionaries of suspected Java classes with package names and line numbers that might be involved in the issues (limit to top 5 classes) example :-
       SUSPECTED_CLASSES: {sus_classes}. 
       **If you think there are no classes to be suspected, then provide an empty list.**
       ensure that the SUSPECTED_CLASSES strictly obey the format curly bracket dictionaries inside one square bracket pair.
    5. Also given that another llm call will do a futher analysis with the java classes, provide the error message to be given in that llm call. It should be in the format:
         ERROR_MESSAGE: "error message"

    ## Important Note
    Note that your response will be directly written into a pdf report, so please ensure to fromat your response accordingly. **Do not leave indentation spaces in the response**. Start all sentences at the begining of a newline.
    """
    return log_analysis_prompt

def get_class_analysis_prompt(customer_problem, class_files_content, error_message_text, log_analysis):
    # Create a prompt for class file analysis
    class_analysis_prompt = f"""
    # You are a software engineer at wso2 and you are analyzing Java class files related to the following customer problem to identify potential issues.
    
    ## Customer Problem
    {customer_problem}

    ## Initial Log Analysis
    {log_analysis}
    
    ## Identified issue in the logs
    {error_message_text}

    ## Suspected Class Files
    The following are the contents of suspected class files related to the issue: (please note that the line number of the issue can be slightly different from the one given)
    
    {json.dumps(class_files_content, indent=2)}
    
    ## Analysis Request
    1. Analyze these class files to identify potential issues related to the customer problem and initial log analysis. If you think there is no need to analyze the class files, then provide a message saying that.
    2. Look for:
       - Design flaws
       - Error handling issues
       - Resource management problems
       - Threading or concurrency issues
       - Any other code smells or anti-patterns
    3. Provide a detailed analysis for each class
    4. Suggest specific improvements or fixes

    **Kepp the analysis to a precise and concise format.**

    ## Important Note
    Note that your response will be directly written into a pdf report, so please ensure to fromat your response accordingly. **Do not leave indentation spaces in the response**. Start all sentences at the begining of a newline.
    """
    return class_analysis_prompt

def get_diagnostic_conclusion_prompt(customer_problem, log_analysis, comprehensive_thread_analysis, class_analysis):
    diagnostic_conclusion_prompt = f"""
    Based on the following information, provide a comprehensive diagnostic conclusion and actionable suggestions:
    
    CUSTOMER PROBLEM:
    {customer_problem}
    
    LOG FILE ANALYSIS:
    {log_analysis}
    
    THREAD DUMP ANALYSIS:
    {comprehensive_thread_analysis}
    
    CLASS ANALYSIS:
    {class_analysis}
    
    Please provide:
    1. A clear diagnosis of the root cause. Be specific and concise.
    2. Specific actionable steps to resolve the issue. If applicable, specially mention if we can try increasing any thread pool sizes.

     ## Important Note
    Note that your response will be directly written into a pdf report, so please ensure to fromat your response accordingly. **Do not leave indentation spaces in the response**. Start all sentences at the begining of a newline.
    """
    return diagnostic_conclusion_prompt
