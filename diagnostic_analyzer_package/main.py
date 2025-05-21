import json
import os
import sys
import logging

from .thread_analyzer import analyze_thread_dumps_and_extract_problems, get_comprehensive_thread_analysis
from .log_analyzer import get_log_content, analyze_error_log, fetch_and_analyze_files
from .utils import read_package_file, pretty_print
from .report import write_final_report
from .final_analyzer import get_diagnostic_conclusion

# Configure logger
logger = logging.getLogger("diagnostic_analyzer")

def main():
    """
    Main function that runs the diagnostic tool in an interactive flow.
    """
    try:
        # ASCII art banner for CLI
        banner = """
        ╔════════════════════════════════════════════════════════════╗
        ║                                                            ║
        ║             DIAGNOSTIC ANALYZER TOOL                       ║
        ║                                                            ║
        ╚════════════════════════════════════════════════════════════╝
        """
        
        logger.info(banner)
        logger.info("Welcome to the Diagnostic Analyzer Tool!")
        logger.info("This tool helps analyze thread dumps and error logs to diagnose issues.")
        logger.info("\nPlease follow the interactive prompts below:")
        
        # Step 1: Ask for customer problem description
        logger.info("\n" + "="*70)
        logger.info("STEP 1: Customer Problem Description")
        logger.info("="*70)
        customer_problem = input("Enter the description of the customer's problem: ")
        
        # Step 2: Ask for folder path
        logger.info("\n" + "="*70)
        logger.info("STEP 2: Diagnostic Data Location")
        logger.info("="*70)
        folder_path = input("Enter the path to the folder containing thread dumps and logs: ")
        
        # Validate folder path
        if not os.path.exists(folder_path):
            logger.error(f"The specified folder path '{folder_path}' does not exist.")
            return
        
        # Load the thread groups configuration
        try:
            thread_groups_config = json.loads(read_package_file('ThreadGroups.json'))
        except Exception as error:
            logger.error(f"Failed to read ThreadGroups.json: {error}")
            return
        
        # Step 3: Analyze thread dumps and extract problematic threads
        logger.info("\n" + "="*70)
        logger.info("STEP 3: Thread Dump Analysis")
        logger.info("="*70)
        thread_analysis, problem_threads = analyze_thread_dumps_and_extract_problems(
            thread_groups_config, folder_path, customer_problem
        )
        
        # Display summary of thread analysis
        if thread_analysis and "THREADS_FOR_ANALYSIS" in thread_analysis:
            logger.info("Initial thread dump analysis completed successfully.")
            
            if problem_threads:
                logger.info(f"Found {len(problem_threads)} problematic threads:")
                for thread in problem_threads:
                    logger.info(f"  - {thread}")
            else:
                logger.info("No problematic threads were identified.")
        else:
            logger.warning("Thread dump analysis did not yield expected results.")

        log_content = get_log_content(folder_path)

        # Step 4: Comprehensive thread analysis with stack traces
        logger.info("\n" + "="*70)
        logger.info("STEP 4: Comprehensive Thread Analysis")
        logger.info("="*70)
        comprehensive_thread_analysis = "Not applicable - no problematic threads identified."
        
        if problem_threads:
            comprehensive_thread_analysis = get_comprehensive_thread_analysis(
                thread_analysis, problem_threads, customer_problem, log_content
            )
            logger.info("Comprehensive thread analysis completed.")
        else:
            logger.info("Skipping comprehensive thread analysis as no problematic threads were identified.")
        
        # Step 5: Get log content and analyze
        logger.info("\n" + "="*70)
        logger.info("STEP 5: Log Analysis")
        logger.info("="*70)
        
        if log_content:
            log_analysis, suspected_classes, error_message = analyze_error_log(log_content, customer_problem)

            logger.info(f"Log analysis completed. error in the log - {error_message}")
            
            # Display summary of log analysis
            if suspected_classes:
                logger.info(f"Found {len(suspected_classes)} suspected classes:")
                for class_name in suspected_classes:
                    logger.info(f"  - {class_name}")
            else:
                logger.info("No specific classes were identified as suspicious in logs.")
        else:
            logger.warning("No log.txt file found in the specified folder.")
            log_analysis = "No log content available for analysis."
            suspected_classes = []
        
        # Step 6: Ask if user wants to analyze class files
        class_analysis = None
        
        if suspected_classes:
            logger.info("\n" + "="*70)
            logger.info("STEP 6: Class File Analysis (Optional)")
            logger.info("="*70)
            
            analyze_choice = input(f"Would you like to analyze the {len(suspected_classes)} suspected class files? (yes/no): ").strip().lower()
            
            if analyze_choice in ['y', 'yes']:
                # Let user choose which classes to analyze
                logger.info("\nAvailable classes for analysis:")
                for i, class_name in enumerate(suspected_classes, 1):
                    logger.info(f"{i}. {class_name}")
                
                selected_indices = input("\nEnter the numbers of classes to analyze (comma-separated, or 'all'): ").strip()
                
                if selected_indices.lower() == 'all':
                    classes_to_analyze = suspected_classes
                else:
                    try:
                        indices = [int(idx.strip()) - 1 for idx in selected_indices.split(',') if idx.strip()]
                        classes_to_analyze = [suspected_classes[idx] for idx in indices if 0 <= idx < len(suspected_classes)]
                    except (ValueError, IndexError):
                        logger.warning("Invalid selection. No classes will be analyzed.")
                        classes_to_analyze = []
                
                if classes_to_analyze:
                    class_analysis = fetch_and_analyze_files(classes_to_analyze, customer_problem, error_message, log_analysis)
                    logger.info("Class analysis completed.")
                else:
                    logger.info("No classes selected for analysis.")
            else:
                logger.info("Skipping class file analysis.")
        
        # Step 7: Generate final report
        logger.info("\n" + "="*70)
        logger.info("STEP 7: Final Report Generation")
        logger.info("="*70)

        final_report = get_diagnostic_conclusion(customer_problem, log_analysis, comprehensive_thread_analysis, class_analysis)
        
        report_file = write_final_report(
            customer_problem, 
            log_analysis, 
            comprehensive_thread_analysis, 
            class_analysis,
            final_report
        )
        
        logger.info(f"Analysis complete! Final report generated: {report_file}")
        logger.info("\nThank you for using the Diagnostic Analyzer Tool!")
        
    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
