# import json
# import os
# import sys

# from .thread_analyzer import analyze_thread_dumps_and_extract_problems, get_comprehensive_thread_analysis
# from .log_analyzer import get_log_content, analyze_error_log, fetch_and_analyze_files
# from .utils import read_package_file, pretty_print
# from .report import write_final_report
# from .final_analyzer import get_diagnostic_conclusion

# def main():
#     """
#     Main function that runs the diagnostic tool in an interactive flow.
#     """
#     try:
#         # ASCII art banner for CLI
#         banner = """
#         ╔════════════════════════════════════════════════════════════╗
#         ║                                                            ║
#         ║             DIAGNOSTIC ANALYZER TOOL                       ║
#         ║                                                            ║
#         ╚════════════════════════════════════════════════════════════╝
#         """
        
#         print(banner)
#         print("Welcome to the Diagnostic Analyzer Tool!")
#         print("This tool helps analyze thread dumps and error logs to diagnose issues.")
#         print("\nPlease follow the interactive prompts below:")
        
#         # Step 1: Ask for customer problem description
#         print("\n" + "="*70)
#         print("STEP 1: Customer Problem Description")
#         print("="*70)
#         customer_problem = input("Enter the description of the customer's problem: ")
        
#         # Step 2: Ask for folder path
#         print("\n" + "="*70)
#         print("STEP 2: Diagnostic Data Location")
#         print("="*70)
#         folder_path = input("Enter the path to the folder containing thread dumps and logs: ")
        
#         # Validate folder path
#         if not os.path.exists(folder_path):
#             pretty_print(f"The specified folder path '{folder_path}' does not exist.", "error")
#             return
        
#         # Load the thread groups configuration
#         try:
#             thread_groups_config = json.loads(read_package_file('ThreadGroups.json'))
#         except Exception as error:
#             pretty_print(f"Failed to read ThreadGroups.json: {error}", "error")
#             return
        
#         # Step 3: Analyze thread dumps and extract problematic threads
#         print("\n" + "="*70)
#         print("STEP 3: Thread Dump Analysis")
#         print("="*70)
#         thread_analysis, problem_threads = analyze_thread_dumps_and_extract_problems(
#             thread_groups_config, folder_path, customer_problem
#         )
        
#         # Display summary of thread analysis
#         if thread_analysis and "THREADS_FOR_ANALYSIS" in thread_analysis:
#             pretty_print("Initial thread dump analysis completed successfully.", "success")
            
#             if problem_threads:
#                 pretty_print(f"Found {len(problem_threads)} problematic threads:", "info")
#                 for thread in problem_threads:
#                     print(f"  - {thread}")
#             else:
#                 pretty_print("No problematic threads were identified.", "info")
#         else:
#             pretty_print("Thread dump analysis did not yield expected results.", "warning")

#         log_content = get_log_content(folder_path)

#         # Step 4: Comprehensive thread analysis with stack traces
#         print("\n" + "="*70)
#         print("STEP 4: Comprehensive Thread Analysis")
#         print("="*70)
#         comprehensive_thread_analysis = "Not applicable - no problematic threads identified."
        
#         if problem_threads:
#             comprehensive_thread_analysis = get_comprehensive_thread_analysis(
#                 thread_analysis, problem_threads, customer_problem, log_content
#             )
#             pretty_print("Comprehensive thread analysis completed.", "success")
#         else:
#             pretty_print("Skipping comprehensive thread analysis as no problematic threads were identified.", "info")
        
#         # Step 5: Get log content and analyze
#         print("\n" + "="*70)
#         print("STEP 5: Log Analysis")
#         print("="*70)
        
#         if log_content:
#             log_analysis, suspected_classes, error_message = analyze_error_log(log_content, customer_problem)

#             pretty_print(f"Log analysis completed. error in the log - {error_message}", "success")
            
#             # Display summary of log analysis
#             if suspected_classes:
#                 pretty_print(f"Found {len(suspected_classes)} suspected classes:", "info")
#                 for class_name in suspected_classes:
#                     print(f"  - {class_name}")
#             else:
#                 pretty_print("No specific classes were identified as suspicious in logs.", "info")
#         else:
#             pretty_print("No log.txt file found in the specified folder.", "warning")
#             log_analysis = "No log content available for analysis."
#             suspected_classes = []
        
#         # Step 6: Ask if user wants to analyze class files
#         class_analysis = None
        
#         if suspected_classes:
#             print("\n" + "="*70)
#             print("STEP 6: Class File Analysis (Optional)")
#             print("="*70)
            
#             analyze_choice = input(f"Would you like to analyze the {len(suspected_classes)} suspected class files? (yes/no): ").strip().lower()
            
#             if analyze_choice in ['y', 'yes']:
#                 # Let user choose which classes to analyze
#                 print("\nAvailable classes for analysis:")
#                 for i, class_name in enumerate(suspected_classes, 1):
#                     print(f"{i}. {class_name}")
                
#                 selected_indices = input("\nEnter the numbers of classes to analyze (comma-separated, or 'all'): ").strip()
                
#                 if selected_indices.lower() == 'all':
#                     classes_to_analyze = suspected_classes
#                 else:
#                     try:
#                         indices = [int(idx.strip()) - 1 for idx in selected_indices.split(',') if idx.strip()]
#                         classes_to_analyze = [suspected_classes[idx] for idx in indices if 0 <= idx < len(suspected_classes)]
#                     except (ValueError, IndexError):
#                         pretty_print("Invalid selection. No classes will be analyzed.", "warning")
#                         classes_to_analyze = []
                
#                 if classes_to_analyze:
#                     class_analysis = fetch_and_analyze_files(classes_to_analyze, customer_problem, error_message, log_analysis)
#                     pretty_print("Class analysis completed.", "success")
#                 else:
#                     pretty_print("No classes selected for analysis.", "info")
#             else:
#                 pretty_print("Skipping class file analysis.", "info")
        
#         # Step 7: Generate final report
#         print("\n" + "="*70)
#         print("STEP 7: Final Report Generation")
#         print("="*70)

#         final_report = get_diagnostic_conclusion(customer_problem, log_analysis, comprehensive_thread_analysis, class_analysis)
        
#         report_file = write_final_report(
#             customer_problem, 
#             log_analysis, 
#             comprehensive_thread_analysis, 
#             class_analysis,
#             final_report
#         )
        
#         pretty_print(f"Analysis complete! Final report generated: {report_file}", "success")
#         print("\nThank you for using the Diagnostic Analyzer Tool!")
        
#     except KeyboardInterrupt:
#         pretty_print("\nOperation cancelled by user.", "warning")
#         sys.exit(1)
#     except Exception as e:
#         pretty_print(f"An unexpected error occurred: {str(e)}", "error")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)


# if __name__ == "__main__":
#     main()
