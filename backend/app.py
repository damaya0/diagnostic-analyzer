from flask import Flask, render_template, request, jsonify, session, redirect, send_file
from dotenv import load_dotenv
import base64
import sys
import os
import json
from io import BytesIO
from datetime import timedelta
from flask_cors import CORS
from flask import Response

# Add the parent directory to the path so we can import the diagnostic package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from diagnostic_analyzer_package.thread_analyzer import analyze_thread_dumps_and_extract_problems, get_comprehensive_thread_analysis
from diagnostic_analyzer_package.log_analyzer import get_log_content, analyze_error_log, fetch_and_analyze_files
from diagnostic_analyzer_package.utils import read_package_file
from diagnostic_analyzer_package.report import write_final_report
from diagnostic_analyzer_package.final_analyzer import get_diagnostic_conclusion

app = Flask(__name__)
CORS(app) 

load_dotenv()
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Session lifetime
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Limit uploads to 50MB
app.config['GITHUB_API_KEY'] = os.getenv('GITHUB_API_KEY')
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Load thread groups configuration
thread_groups_config = json.loads(read_package_file('ThreadGroups.json'))

@app.route('/analyze', methods=['POST'])
def analyze():
    # Get form data
    customer_problem = request.form.get('customer_problem', '')
    
    # Handle file upload
    if 'diagnostic_files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    
    # Save uploaded files to the temp directory
    files = request.files.getlist('diagnostic_files')

    print(f"\n[INFO] Received {len(files)} files for analysis.")

    in_memory_files = {}
    for file in files:
            file_content = file.read()
            in_memory_file = BytesIO(file_content)
            in_memory_files[file.filename] = in_memory_file
    
    # Analyze thread dumps
    thread_analysis, problem_threads = analyze_thread_dumps_and_extract_problems(
        thread_groups_config, in_memory_files, customer_problem
    )
    
    if problem_threads:
        comprehensive_thread_analysis = get_comprehensive_thread_analysis(
            thread_analysis, problem_threads, customer_problem, log_content
        )
    else:
        comprehensive_thread_analysis = "Not applicable - no problematic threads identified."

    # Get log content
    log_content = get_log_content(in_memory_files)

    if log_content:
        log_analysis, suspected_classes, error_message = analyze_error_log(log_content, customer_problem)
    else:
        log_analysis = "No log content available for analysis."
        suspected_classes = []
        error_message = ""

    # Save analysis data 
    analysis_data = {
        'customerProblem': customer_problem,
        'problemThreads': problem_threads,
        'suspectedClasses': suspected_classes,
        'threadAnalysis': thread_analysis,
        'comprehensiveThreadAnalysis': comprehensive_thread_analysis,
        'logAnalysis': log_analysis,
        'customerProblem': error_message,
    }

    # If there are suspected classes, redirect to class selection
    if suspected_classes:
        return  {"success": True, "analysis_data": analysis_data}
        
    else:
        
        # Store results in a file
        results = {
            'customer_problem': customer_problem,
            'problem_threads': problem_threads,
            'thread_analysis': thread_analysis,
            'comprehensive_thread_analysis': comprehensive_thread_analysis,
            'log_analysis': log_analysis,
            'class_analysis': None
        }

        return ({"success": True, "results": results})

@app.route('/analyze_classes', methods=['POST'])
def analyze_classes():
    # Get JSON data from request
    data = request.get_json(force=True)  # force=True to parse even if content-type is wrong

    # Extract everything from JSON payload
    selected_class_names = data.get('selected_classes', [])
    original_suspected_classes = data.get('suspected_classes', [])
    log_analysis = data.get('log_analysis', '')
    comprehensive_thread_analysis = data.get('comprehensive_thread_analysis', '')
    customer_problem = data.get('customer_problem', '')
    error_message = data.get('error_message', '')
    problem_threads = data.get('problem_threads', [])
    thread_analysis = data.get('thread_analysis', '')

    # Find the full class objects from the original suspected_classes
    selected_classes = []

    # Check if the suspected classes are already in dictionary format
    if original_suspected_classes and isinstance(original_suspected_classes[0], dict):
        # Filter the original suspected classes to only include those selected
        for sus_class in original_suspected_classes:
            if sus_class.get('class') in selected_class_names:
                selected_classes.append(sus_class)
    else:
        # If they're just strings
        print(f"WARNING: suspected_classes are not in dictionary format: {original_suspected_classes}")
        # Create mock dictionaries for the selected classes
        for class_name in selected_class_names:
            # This is a fallback approach - these are dummy values
            selected_classes.append({
                "class": class_name,
                "package": "unknown.package",
                "issue_line": 1
            })

    # Perform class analysis
    class_analysis = None
    if selected_classes:
        try:
            print(f"\n[INFO] Analyzing selected classes: {selected_classes}")
            class_analysis = fetch_and_analyze_files(
                selected_classes,  # Now this is a list of dictionaries
                customer_problem, 
                error_message,
                log_analysis
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Error analyzing classes: {str(e)}"}), 500

    results = {
        "class_analysis": class_analysis,
        "log_analysis": log_analysis,
        "comprehensive_thread_analysis": comprehensive_thread_analysis,
        "customer_problem": customer_problem,
        "problem_threads": problem_threads,
        "thread_analysis": thread_analysis
    }
    
    return jsonify({"success": True, "results": results})

@app.route('/download_report', methods=['POST'])
def download_report():

    # Get JSON data from request
    data = request.get_json(force=True)  # force=True to parse even if content-type is wrong

    # Extract everything from JSON payload
    log_analysis = data.get('log_analysis', '')
    comprehensive_thread_analysis = data.get('comprehensive_thread_analysis', '')
    customer_problem = data.get('customer_problem', '')
    class_analysis = data.get('class_analysis', '')

        # Generate final report
    final_report = get_diagnostic_conclusion(
        customer_problem,
        log_analysis,
        comprehensive_thread_analysis,
        class_analysis
    )
    
    # Generate PDF Report
    buffer = write_final_report(
        customer_problem, 
        log_analysis, 
        comprehensive_thread_analysis, 
        class_analysis=class_analysis, 
        final_report=final_report
    )
    
    return Response(
        buffer,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': 'attachment; filename=final_diagnostic_report.pdf'
        }
    )

if __name__ == "__main__":
    app.run(debug=True)