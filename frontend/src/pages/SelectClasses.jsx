import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './styles.css'; // Adjust the path as necessary
import { useLocation } from 'react-router-dom';
import { last } from 'lodash';

// Props: 
// comprehensiveThreadAnalysis, logAnalysis,  suspectedClasses (array), sessionId
export default function SelectClasses({
  
}) {
    const navigate = useNavigate();
    // const stored = localStorage.getItem('analysisData');

    // const analysisData = stored ? JSON.parse(stored) : {};

    const location = useLocation();
    const analysisData = location.state?.analysis_data;

    console.log("Analysis data---:", analysisData);

    const [selectedClasses, setSelectedClasses] = useState([]);
    const [selectAll, setSelectAll] = useState(false);
    const [loading, setLoading] = useState(null); // 'skip' | 'analyze' | null

    React.useEffect(() => {
        if (!analysisData) {
            navigate('/'); // redirect to home if no results
        }
    }, [analysisData, navigate]);

    if (!analysisData) {
        return null; // Prevent rendering before redirect
    }

    const {
        comprehensiveThreadAnalysis,
        logAnalysis,
        suspectedClasses,
        customerProblem,
        errorMessage,
        problemThreads,
        threadAnalysis
    } = analysisData;

  // Handler for Select All
  const handleSelectAll = (e) => {
    const checked = e.target.checked;
    setSelectAll(checked);
    setSelectedClasses(checked ? suspectedClasses.map(cls => cls.class) : []);
  };

  // Handler for individual checkbox
  const handleClassCheckbox = (e, className) => {
    if (e.target.checked) {
      setSelectedClasses([...selectedClasses, className]);
    } else {
      setSelectedClasses(selectedClasses.filter(c => c !== className));
      setSelectAll(false);
    }
  };

//   localStorage.setItem('selectedClasses', JSON.stringify(selectedClasses));

  // Submit handler
  const handleSubmit = async (e) => {
    e.preventDefault();

        setLoading('analyze');
        try {
            // Construct the payload
            const payload = {
                selected_classes: selectedClasses,
                suspected_classes: suspectedClasses,
                log_analysis: logAnalysis,
                comprehensive_thread_analysis: comprehensiveThreadAnalysis,
                customer_problem: customerProblem,
                error_message: errorMessage,
                problem_threads: problemThreads,
                thread_analysis: threadAnalysis
            };

            const response = await fetch("http://127.0.0.1:8000/analyze_classes", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error("Failed to analyze selected classes.");
            }

            const result = await response.json();
            // Save the `results` object to localStorage

            // console.log("Results data---:", result);
            if (result.results) {
                // localStorage.setItem('results', JSON.stringify(result.results));
                navigate("/results", 
                    {
                        state: {
                            results: result.results
                        }
                    }
                );
            } else {
                // Optional: handle error case
                alert("No results in server response");
            }
        } catch (err) {
            alert(err.message || "An error occurred during analysis.");
        } finally {
            setLoading(null);
        }
  };

  // Skip handler
  const handleSkip = (e) => {
    setLoading('skip');

    navigate("/results", 
        {
            state: {
                results: {
                    class_analysis: null,
                    log_analysis: logAnalysis,
                    comprehensive_thread_analysis: comprehensiveThreadAnalysis,
                    customer_problem: customerProblem,
                    problem_threads: problemThreads,
                    thread_analysis: threadAnalysis,
                    suspected_classes: suspectedClasses
                }
            }
        }
    );
  };

  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-10">
          <div className="card shadow">
            <div className="card-header bg-orange text-white text-center d-flex align-items-center">
              <img 
                src="images/header_image.jpg" 
                alt="Header" 
                className="me-3" 
                style={{ height: '100px', width: 'auto' }}
              />
              <div>
                <h1 className="display-6">Class File Analysis</h1>
                <p className="lead mb-0">Review analysis reports and select classes</p>
              </div>
            </div>
            <div className="card-body">

              {/* Diagnostic Reports */}
              <div className="mb-4">
                <h3 className="h5">Diagnostic Analysis Reports</h3>

                {/* Thread Analysis */}
                {comprehensiveThreadAnalysis && comprehensiveThreadAnalysis !== "Not applicable - no problematic threads identified." && (
                  <div className="mb-4">
                    <h4 className="h6">Thread Analysis</h4>
                    <div className="card bg-light">
                      <div className="card-body">
                        <pre className="mb-0">{comprehensiveThreadAnalysis}</pre>
                      </div>
                    </div>
                  </div>
                )}

                {/* Log Analysis */}
                {logAnalysis && logAnalysis !== "No log content available for analysis." && (
                  <div className="mb-4">
                    <h4 className="h6">Log Analysis</h4>
                    <div className="card bg-light">
                      <div className="card-body">
                        <pre className="mb-0">{logAnalysis}</pre>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Class Selection */}
              <div className="border-top pt-4 mb-4">
                <h3 className="h5">Select Classes for Further Analysis</h3>
                <form id="classSelectionForm" onSubmit={handleSubmit}>

                  <div className="mb-4">

                    <div className="form-check mb-2">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="selectAllClasses"
                        checked={selectAll}
                        onChange={handleSelectAll}
                      />
                      <label className="form-check-label fw-bold" htmlFor="selectAllClasses">
                        Select All Classes
                      </label>
                    </div>

                    <div className="list-group mb-3">
                      {suspectedClasses.map((classDict, idx) => (
                        <div className="list-group-item" key={classDict.class}>
                          <div className="form-check">
                            <input
                              className="form-check-input class-checkbox"
                              type="checkbox"
                              name="selected_classes"
                              value={classDict.class}
                              id={`class${idx + 1}`}
                              checked={selectedClasses.includes(classDict.class)}
                              onChange={(e) => handleClassCheckbox(e, classDict.class)}
                            />
                            <label className="form-check-label" htmlFor={`class${idx + 1}`}>
                              {classDict.class} (package: {classDict.package})
                            </label>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="row g-2">
                    <div className="col">
                      <button
                        type="button"
                        className={`btn btn-primary w-100 ${loading === 'skip' ? 'loading' : ''}`}
                        onClick={handleSkip}
                        disabled={!!loading}
                      >
                        {loading === 'skip' && <span className="spinner-border" role="status" aria-hidden="true"></span>}
                        {loading === 'skip' ? 'Processing...' : 'Skip Class Analysis'}
                      </button>
                    </div>
                    <div className="col">
                      <button
                        type="submit"
                        className={`btn btn-primary w-100 ${loading === 'analyze' ? 'loading' : ''}`}
                        id="analyzeClassesBtn"
                        disabled={!!loading}
                      >
                        {loading === 'analyze' && <span className="spinner-border" role="status" aria-hidden="true"></span>}
                        {loading === 'analyze' ? 'Analyzing...' : 'Analyze Selected Classes'}
                      </button>
                    </div>
                  </div>
                </form>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
