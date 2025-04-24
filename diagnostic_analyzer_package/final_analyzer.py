from .utils import call_chatgpt_api
from .prompts import get_diagnostic_conclusion_prompt

def get_diagnostic_conclusion(customer_problem, log_analysis, comprehensive_thread_analysis, class_analysis):
    """
    Gets a final diagnostic conclusion and suggestions by analyzing multiple inputs.
    
    Args:
        customer_problem (str): Description of the customer's problem
        log_analysis (str): Analysis of log files
        comprehensive_thread_analysis (str): Analysis of thread dumps
        class_analysis (str): Analysis of class files
        
    Returns:
        str: Final conclusion and suggestions
    """

    diagnostic_conclusion_prompt = get_diagnostic_conclusion_prompt(customer_problem, log_analysis, comprehensive_thread_analysis, class_analysis)
    
    # Call the ChatGPT API with the diagnostic_conclusion_prompt
    conclusion = call_chatgpt_api(diagnostic_conclusion_prompt)
    return conclusion