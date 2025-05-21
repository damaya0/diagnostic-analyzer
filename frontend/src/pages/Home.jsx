import { useNavigate } from 'react-router-dom';
import React, { useState, useEffect } from 'react';
import './styles.css'

function Home() {
    const navigate = useNavigate();
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [diagnostic_files, setDiagnosticFiles] = useState([]);
    const [warnings, setWarnings] = useState({
        noThreadDump: false,
        noLogFile: false
    });

    // Validate files whenever diagnostic_files changes
    useEffect(() => {
        // Check if at least one thread dump file exists
        const hasThreadDump = diagnostic_files.some(file =>
            /^threaddump.*$/i.test(file.name)
        );

        // Check if log.txt exists
        const hasLogFile = diagnostic_files.some(file =>
            file.name === "log.txt"
        );

        setWarnings({
            noThreadDump: !hasThreadDump,
            noLogFile: !hasLogFile
        });
    }, [diagnostic_files]);

    const handleFileChange = (e) => {
        setDiagnosticFiles([...e.target.files]);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsAnalyzing(true);
        const formData = new FormData(e.target);
        const customerProblem = formData.get('customer_problem');
        const diagnosticFiles = formData.getAll('diagnostic_files');

        // Validate required fields
        if (!customerProblem) {
            alert('Please enter the customer problem description.');
            setIsAnalyzing(false);
            return;
        }
        if (diagnosticFiles.length === 0) {
            alert('Please upload at least one diagnostic file.');
            setIsAnalyzing(false);
            return;
        }

        // Prevent submission if required files are missing
        if (warnings.noThreadDump || warnings.noLogFile) {
            setIsAnalyzing(false);
            return; // Don't proceed with submission
        }

        // Call the backend API to handle the form submission
        // For example, using fetch:

        console.log('Submitting form with data:', {
            customer_problem: customerProblem,
            diagnostic_files: diagnosticFiles,
        });
        const response = await fetch('http://127.0.0.1:8000/analyze', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            setIsAnalyzing(false);
            throw new Error('Network response was not ok');
        }

        const data = await response.json();  // <--- wait for the JSON to be parsed

        if (data.analysis_data) {

            navigate('/select_classes', {
                state: {
                    analysis_data: data.analysis_data
                }
            });
        }
        if (data.results) {

            navigate('/results',
                {
                    state: {
                        results: data.results
                    }
                }
            );
        }
        setIsAnalyzing(false);
        console.log('Form submitted');
    };

    return (
        <div className="container mt-5">
            <div className="row justify-content-center">
                <div className="col-md-8">
                    <div className="card shadow">
                        <div className="card-header bg-orange text-white text-center d-flex align-items-center">
                            <img
                                src="images/header_image.jpg"
                                alt="Header"
                                className="me-3"
                                style={{ height: '100px', width: 'auto' }}
                            />
                            <div>
                                <h1 className="display-6">Diagnostic Analyzer Tool</h1>
                                <p className="lead mb-0">for WSO2 Micro Integrator</p>
                            </div>
                        </div>
                        <div className="card-body">
                            <form id="diagnosticForm" onSubmit={handleSubmit}>
                                <div className="mb-4">
                                    <label htmlFor="customerProblem" className="form-label">
                                        Customer Problem Description
                                    </label>
                                    <textarea
                                        className="form-control"
                                        id="customerProblem"
                                        name="customer_problem"
                                        rows="4"
                                        placeholder="Enter the description of the customer's problem..."
                                        required
                                    ></textarea>
                                </div>

                                <div className="mb-4">
                                    <label className="form-label">Diagnostic Files</label>
                                    <div className="input-group">
                                        <input
                                            type="file"
                                            className="form-control"
                                            id="diagnosticFiles"
                                            name="diagnostic_files"
                                            multiple
                                            required
                                            onChange={handleFileChange}
                                        />
                                    </div>
                                </div>

                                {/* Display warnings if needed */}
                                {warnings.noThreadDump && (
                                    <div className="warning-message">
                                        Please select at least one thread dump file
                                    </div>
                                )}

                                {warnings.noLogFile && (
                                    <div className="warning-message">
                                        Please select the log file (named log.txt)
                                    </div>
                                )}

                                <div className="d-grid gap-2">
                                    <button
                                        type="submit"
                                        className={`btn btn-primary ${isAnalyzing ? 'loading' : ''}`}
                                        id="analyzeBtn"
                                        disabled={isAnalyzing || warnings.noThreadDump || warnings.noLogFile}
                                    >
                                        {isAnalyzing && <span className="spinner-border" role="status" aria-hidden="true"></span>}
                                        {isAnalyzing ? 'Analyzing...' : 'Analyze'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Home;
