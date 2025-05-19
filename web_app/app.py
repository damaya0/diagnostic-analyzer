from flask import Flask, render_template, request, jsonify, session, redirect, send_file
from dotenv import load_dotenv
import sys
import os
import json
import tempfile
import shutil
import uuid
import threading
from io import BytesIO
from datetime import datetime, timedelta, timezone

# Add the parent directory to the path so we can import the diagnostic package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from diagnostic_analyzer_package.thread_analyzer import analyze_thread_dumps_and_extract_problems, get_comprehensive_thread_analysis
from diagnostic_analyzer_package.log_analyzer import get_log_content, analyze_error_log, fetch_and_analyze_files
from diagnostic_analyzer_package.utils import read_package_file, cleanup_thread
from diagnostic_analyzer_package.report import write_final_report
from diagnostic_analyzer_package.final_analyzer import get_diagnostic_conclusion

app = Flask(__name__)
# Load environment variables from .env file
load_dotenv()
app.secret_key = '12345678901234567890' ##env
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Session lifetime
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions on server filesystem instead of cookies
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Limit uploads to 50MB
app.config['GITHUB_API_KEY'] = os.getenv('GITHUB_API_KEY')
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Create a directory to store session files
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# This will serve as our database
memory_store = {
    'analysis_data': {},  # Indexed by session_id
    'results': {}         # Indexed by session_id
}

# Store timestamps of when data was added
data_timestamps = {}

# Load thread groups configuration
thread_groups_config = json.loads(read_package_file('ThreadGroups.json'))

# Start the cleanup thread when the app starts
cleanup_thread_instance = threading.Thread(target=cleanup_thread,args=(memory_store, data_timestamps), daemon=True)
cleanup_thread_instance.start()

@app.route('/')
def index():
    # Make session permanent
    session.permanent = True
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    # Get form data
    customer_problem = request.form.get('customer_problem', '')
    
    # Handle file upload
    if 'diagnostic_files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    
    # Save uploaded files to the temp directory
    files = request.files.getlist('diagnostic_files')

    in_memory_files = {}
    for file in files:
            # Read the file into memory
            file_content = file.read()
            # Create a BytesIO object that acts like a file
            in_memory_file = BytesIO(file_content)
            # Store with filename for reference
            in_memory_files[file.filename] = in_memory_file
    
    print(in_memory_files)

    # Analyze thread dumps
    thread_analysis, problem_threads = analyze_thread_dumps_and_extract_problems(
        thread_groups_config, in_memory_files, customer_problem
    )
    
    # Get log content
    log_content = get_log_content(in_memory_files)
    
    if problem_threads:
        comprehensive_thread_analysis = get_comprehensive_thread_analysis(
            thread_analysis, problem_threads, customer_problem, log_content
        )
    else:
        comprehensive_thread_analysis = "Not applicable - no problematic threads identified."
    
    # Log analysis
    log_analysis = "No log content available for analysis."
    suspected_classes = []
    error_message = ""
    
    if log_content:
        log_analysis, suspected_classes, error_message = analyze_error_log(log_content, customer_problem)
    
    # Save analysis data to a file instead of session
    analysis_data = {
        'customer_problem': customer_problem,
        'problem_threads': problem_threads,
        'suspected_classes': suspected_classes,
        'thread_analysis': thread_analysis,
        'comprehensive_thread_analysis': comprehensive_thread_analysis,
        'log_analysis': log_analysis,
        'error_message': error_message,
    }
    
    # Store in memory_store and update timestamp
    memory_store['analysis_data'][session_id] = analysis_data
    data_timestamps[session_id] = datetime.now(timezone.utc)

    # If there are suspected classes, redirect to class selection
    if suspected_classes:
        return jsonify({"success": True, "redirect": f"/select_classes?session_id={session_id}"})
    else:
        # No classes to analyze, generate final report
        final_report = get_diagnostic_conclusion(
            customer_problem, log_analysis, comprehensive_thread_analysis, None
        )
        
        # Store results in a file
        results = {
            'customer_problem': customer_problem,
            'problem_threads': problem_threads,
            'suspected_classes': suspected_classes,
            'thread_analysis': thread_analysis,
            'comprehensive_thread_analysis': comprehensive_thread_analysis,
            'log_analysis': log_analysis,
            'final_report': final_report,
            'class_analysis': None
        }

        # Store in memory_store and update timestamp
        memory_store['results'][session_id] = results
        data_timestamps[session_id] = datetime.now(timezone.utc)
        
        return jsonify({"success": True, "redirect": f"/results?session_id={session_id}"})

@app.route('/select_classes')
def select_classes():
    session_id = request.args.get('session_id')
    if not session_id:
        session_id = session.get('session_id')
        
    if not session_id:
        return render_template('error.html', error="Session expired or invalid. Please start a new analysis.")
    
    # Get analysis data from memory
    analysis_data = memory_store['analysis_data'][session_id]
    
    # Update timestamp to indicate recent access
    data_timestamps[session_id] = datetime.now(timezone.utc)
    
    # Store session ID in session for future requests
    session['session_id'] = session_id
    
    return render_template('select_classes.html', 
                          suspected_classes=analysis_data.get('suspected_classes', []),
                          class_count=len(analysis_data.get('suspected_classes', [])),
                          session_id=session_id,
                          comprehensive_thread_analysis=analysis_data.get('comprehensive_thread_analysis'),
                          problem_threads=analysis_data.get('problem_threads', []),
                          log_analysis=analysis_data.get('log_analysis'))

@app.route('/analyze_classes', methods=['POST'])
def analyze_classes():
    session_id = request.form.get('session_id') or session.get('session_id')
    
    if not session_id:
        return jsonify({"error": "Session expired or invalid"}), 400
    
    # Get analysis data from memory
    analysis_data = memory_store['analysis_data'][session_id]
    
    # Get selected classes
    selected_class_names = request.form.getlist('selected_classes')
    
    # Find the full class objects from the original suspected_classes
    original_suspected_classes = analysis_data.get('suspected_classes', [])
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
                analysis_data['customer_problem'], 
                analysis_data.get('error_message', ''),
                analysis_data['log_analysis']
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Error analyzing classes: {str(e)}"}), 500
    
    # Generate final report
    final_report = get_diagnostic_conclusion(
        analysis_data['customer_problem'],
        analysis_data['log_analysis'],
        analysis_data['comprehensive_thread_analysis'],
        class_analysis
    )
    
    # Generate PDF Report
    report_path = write_final_report(
        analysis_data['customer_problem'], 
        analysis_data['log_analysis'], 
        analysis_data['comprehensive_thread_analysis'], 
        class_analysis=class_analysis, 
        final_report=final_report
    )
    
    # Save the report path to access it later
    unique_report_name = f"{session_id}_final_report.pdf"
    report_save_path = os.path.join(REPORTS_DIR, unique_report_name)
    
    # Copy the report to our reports directory
    if report_path and os.path.exists(report_path):
        shutil.copy(report_path, report_save_path)
    
    # Store results in a file
    results = {
        'customer_problem': analysis_data['customer_problem'],
        'problem_threads': analysis_data['problem_threads'],
        'suspected_classes': analysis_data['suspected_classes'],
        'thread_analysis': analysis_data['thread_analysis'],
        'comprehensive_thread_analysis': analysis_data['comprehensive_thread_analysis'],
        'log_analysis': analysis_data['log_analysis'],
        'final_report': final_report,
        'class_analysis': class_analysis,
        'analyzed_classes': selected_classes,
        'report_path': unique_report_name
    }
    
    # Store in memory_store and update timestamp
    memory_store['results'][session_id] = results
    data_timestamps[session_id] = datetime.now(timezone.utc)
    
    return jsonify({"success": True, "redirect": f"/results?session_id={session_id}"})

@app.route('/skip_class_analysis', methods=['GET'])
def skip_class_analysis():
    session_id = request.args.get('session_id')
    if not session_id:
        session_id = session.get('session_id')
        
    if not session_id:
        return render_template('error.html', error="Session expired or invalid. Please start a new analysis.")
    
    # Get analysis data from memory
    analysis_data = memory_store['analysis_data'][session_id]
    
    # Generate final report without class analysis
    try:
        final_report = get_diagnostic_conclusion(
            analysis_data['customer_problem'],
            analysis_data['log_analysis'],
            analysis_data['comprehensive_thread_analysis'],
            None  # No class analysis
        )
    except Exception as e:
        print(f"Error generating final report: {e}")
        final_report = "Error generating final diagnostic report."
    
    # Generate PDF Report
    report_path = write_final_report(
        analysis_data['customer_problem'], 
        analysis_data['log_analysis'], 
        analysis_data['comprehensive_thread_analysis'], 
        class_analysis=None, 
        final_report=final_report
    )
    
    # Save the report path to access it later
    unique_report_name = f"{session_id}_final_report.pdf"
    report_save_path = os.path.join(REPORTS_DIR, unique_report_name)
    
    # Copy the report to our reports directory
    if report_path and os.path.exists(report_path):
        shutil.copy(report_path, report_save_path)
    
    # Store results in a file
    results = {
        'customer_problem': analysis_data['customer_problem'],
        'problem_threads': analysis_data['problem_threads'],
        'suspected_classes': analysis_data['suspected_classes'],
        'thread_analysis': analysis_data['thread_analysis'],
        'comprehensive_thread_analysis': analysis_data['comprehensive_thread_analysis'],
        'log_analysis': analysis_data['log_analysis'],
        'final_report': final_report,
        'class_analysis': None,
        'analyzed_classes': [],  # No classes were analyzed
        'report_path': unique_report_name
    }
    
    # Store in memory_store and update timestamp
    memory_store['results'][session_id] = results
    data_timestamps[session_id] = datetime.now(timezone.utc)
    
    # Redirect to results page
    return redirect(f'/results?session_id={session_id}')

@app.route('/results')
def results():
    session_id = request.args.get('session_id')
    if not session_id:
        session_id = session.get('session_id')
        
    if not session_id:
        return render_template('error.html', error="Session expired or invalid. Please start a new analysis.")
    
    # Get results from memory
    analysis_results = memory_store['results'][session_id]
    
    # Update timestamp
    data_timestamps[session_id] = datetime.now(timezone.utc)
    
    return render_template('results.html', results=analysis_results)

@app.route('/download_report/<filename>')
def download_report(filename):
    """Download the generated final report"""
    report_path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(report_path):
        return render_template('error.html', error="Report file not found. It may have been deleted.")
    
    return send_file(report_path, as_attachment=True)

@app.route('/error')
def error():
    error_message = request.args.get('message', 'An unknown error occurred')
    return render_template('error.html', error=error_message)

# Cleanup old report files periodically
def cleanup_old_report_files():
    """Delete session files older than 2 hours"""
    import time
    now = time.time()

    for filename in os.listdir(REPORTS_DIR):
        filepath = os.path.join(REPORTS_DIR, filename)
        if os.path.isfile(filepath):
            file_modified = os.path.getmtime(filepath)
            if now - file_modified > 7200:  # 2 hours in seconds
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Error removing old report file {filepath}: {e}")

# Clean up on startup
cleanup_old_report_files()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)