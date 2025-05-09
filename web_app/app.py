from flask import Flask, render_template, request, jsonify, session, redirect, send_file
import sys
import os
import json
import tempfile
import shutil
import pickle
from datetime import timedelta

# Add the parent directory to the path so we can import the diagnostic package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from diagnostic_analyzer_package.thread_analyzer import analyze_thread_dumps_and_extract_problems, get_comprehensive_thread_analysis
from diagnostic_analyzer_package.log_analyzer import get_log_content, analyze_error_log, fetch_and_analyze_files
from diagnostic_analyzer_package.utils import read_package_file
from diagnostic_analyzer_package.report import write_final_report
from diagnostic_analyzer_package.final_analyzer import get_diagnostic_conclusion

app = Flask(__name__)
app.secret_key = '12345678901234567890'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Session lifetime
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions on server filesystem instead of cookies
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Limit uploads to 50MB

# Create a directory to store session files
os.makedirs(os.path.join(os.path.dirname(__file__), 'session_data'), exist_ok=True)
SESSION_FILE_DIR = os.path.join(os.path.dirname(__file__), 'session_data')
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# Store temporary directory paths
temp_dirs = {}

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
    
    temp_dir = tempfile.mkdtemp()
    
    # Generate a unique session ID
    import uuid
    session_id = str(uuid.uuid4())
    temp_dirs[session_id] = temp_dir
    session['session_id'] = session_id
    
    # Save uploaded files to the temp directory
    files = request.files.getlist('diagnostic_files')
    for file in files:
        file.save(os.path.join(temp_dir, file.filename))
    
    # Load thread groups configuration
    try:
        thread_groups_config = json.loads(read_package_file('ThreadGroups.json'))
    except Exception as error:
        return jsonify({"error": f"Failed to read ThreadGroups.json: {error}"}), 500
    
    # Analyze thread dumps
    thread_analysis, problem_threads = analyze_thread_dumps_and_extract_problems(
        thread_groups_config, temp_dir, customer_problem
    )
    
    # Get log content
    log_content = get_log_content(temp_dir)
    
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
        'temp_dir': temp_dir
    }
    
    # Save analysis data to a file
    data_file = os.path.join(SESSION_FILE_DIR, f"{session_id}.pkl")
    with open(data_file, 'wb') as f:
        pickle.dump(analysis_data, f)
    
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
        
        # Generate PDF Report
        report_path = write_final_report(
            customer_problem, 
            log_analysis, 
            comprehensive_thread_analysis, 
            class_analysis=None, 
            final_report=final_report
        )
        
        # Save the report path to access it later
        unique_report_name = f"{session_id}_final_report.pdf"
        report_save_path = os.path.join(REPORTS_DIR, unique_report_name)
        
        # Copy the report to our reports directory
        if report_path and os.path.exists(report_path):
            shutil.copy(report_path, report_save_path)
            # Add report path to results
            results['report_path'] = unique_report_name
        
        results_file = os.path.join(SESSION_FILE_DIR, f"{session_id}_results.pkl")
        with open(results_file, 'wb') as f:
            pickle.dump(results, f)
        
        # Clean up temporary directory
        clean_temp_dir(session_id)
        
        return jsonify({"success": True, "redirect": f"/results?session_id={session_id}"})

@app.route('/select_classes')
def select_classes():
    session_id = request.args.get('session_id')
    if not session_id:
        session_id = session.get('session_id')
        
    if not session_id:
        return render_template('error.html', error="Session expired or invalid. Please start a new analysis.")
    
    # Load analysis data from file
    data_file = os.path.join(SESSION_FILE_DIR, f"{session_id}.pkl")
    try:
        with open(data_file, 'rb') as f:
            analysis_data = pickle.load(f)
    except (FileNotFoundError, pickle.PickleError):
        return render_template('error.html', error="Session data not found. Please start a new analysis.")
    
    # Store session ID in session for future requests
    session['session_id'] = session_id
    
    return render_template('select_classes.html', 
                          suspected_classes=analysis_data.get('suspected_classes', []),
                          class_count=len(analysis_data.get('suspected_classes', [])),
                          session_id=session_id,
                          # Pass the report data needed for display
                          comprehensive_thread_analysis=analysis_data.get('comprehensive_thread_analysis'),
                          problem_threads=analysis_data.get('problem_threads', []),
                          log_analysis=analysis_data.get('log_analysis'))

@app.route('/analyze_classes', methods=['POST'])
def analyze_classes():
    session_id = request.form.get('session_id') or session.get('session_id')
    
    if not session_id:
        return jsonify({"error": "Session expired or invalid"}), 400
    
    # Load analysis data from file
    data_file = os.path.join(SESSION_FILE_DIR, f"{session_id}.pkl")
    try:
        with open(data_file, 'rb') as f:
            analysis_data = pickle.load(f)
    except (FileNotFoundError, pickle.PickleError):
        return jsonify({"error": "Session data not found"}), 400
    
    # Get selected classes (just the names)
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
    
    # Get temp directory from analysis data
    temp_dir = analysis_data.get('temp_dir')
    if not temp_dir or not os.path.exists(temp_dir):
        return jsonify({"error": "Temporary directory not found"}), 400
    
    # Perform class analysis
    class_analysis = None
    if selected_classes:
        try:
            print(f"\n[INFO] Analyzing selected classes: {selected_classes}")
            class_analysis = fetch_and_analyze_files(
                selected_classes,  # Now this is a list of dictionaries
                analysis_data['customer_problem'], 
                analysis_data.get('error_message', '')
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
    
    results_file = os.path.join(SESSION_FILE_DIR, f"{session_id}_results.pkl")
    with open(results_file, 'wb') as f:
        pickle.dump(results, f)
    
    # Clean up temporary directory and analysis data file
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.remove(data_file)
    except Exception as e:
        print(f"Error cleaning up: {e}")
    
    return jsonify({"success": True, "redirect": f"/results?session_id={session_id}"})

@app.route('/skip_class_analysis', methods=['GET'])
def skip_class_analysis():
    session_id = request.args.get('session_id')
    if not session_id:
        session_id = session.get('session_id')
        
    if not session_id:
        return render_template('error.html', error="Session expired or invalid. Please start a new analysis.")
    
    # Load analysis data from file
    data_file = os.path.join(SESSION_FILE_DIR, f"{session_id}.pkl")
    try:
        with open(data_file, 'rb') as f:
            analysis_data = pickle.load(f)
    except (FileNotFoundError, pickle.PickleError):
        return render_template('error.html', error="Session data not found. Please start a new analysis.")
    
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
    
    results_file = os.path.join(SESSION_FILE_DIR, f"{session_id}_results.pkl")
    with open(results_file, 'wb') as f:
        pickle.dump(results, f)
    
    # Clean up the temp directory and analysis data file
    try:
        temp_dir = analysis_data.get('temp_dir')
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.remove(data_file)
    except Exception as e:
        print(f"Error cleaning up: {e}")
    
    # Redirect to results page
    return redirect(f'/results?session_id={session_id}')

@app.route('/results')
def results():
    session_id = request.args.get('session_id')
    if not session_id:
        session_id = session.get('session_id')
        
    if not session_id:
        return render_template('error.html', error="Session expired or invalid. Please start a new analysis.")
    
    # Load results from file
    results_file = os.path.join(SESSION_FILE_DIR, f"{session_id}_results.pkl")
    try:
        with open(results_file, 'rb') as f:
            analysis_results = pickle.load(f)
    except (FileNotFoundError, pickle.PickleError):
        return render_template('error.html', error="Results not found. Please start a new analysis.")
    
    # Clean up results file after reading
    try:
        os.remove(results_file)
    except Exception as e:
        print(f"Error removing results file: {e}")
    
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

def clean_temp_dir(session_id):
    """Clean up temporary directory"""
    if session_id in temp_dirs:
        try:
            if os.path.exists(temp_dirs[session_id]):
                shutil.rmtree(temp_dirs[session_id])
            del temp_dirs[session_id]
        except Exception as e:
            print(f"Error cleaning up temporary directory: {e}")

# Cleanup old session files periodically
def cleanup_old_session_files():
    """Delete session files older than 2 hours"""
    import time
    
    now = time.time()
    for filename in os.listdir(SESSION_FILE_DIR):
        filepath = os.path.join(SESSION_FILE_DIR, filename)
        if os.path.isfile(filepath):
            file_modified = os.path.getmtime(filepath)
            if now - file_modified > 7200:  # 2 hours in seconds
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Error removing old session file {filepath}: {e}")
    
    # Also clean up old reports
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
cleanup_old_session_files()

if __name__ == '__main__':
    app.run(debug=True)