import React from 'react';
import './styles.css'; // Adjust the path as necessary
import { useLocation } from 'react-router-dom';
import html2pdf from 'html2pdf.js';
import { useNavigate } from 'react-router-dom';

export default function Results() {
    const navigate = useNavigate();
    // Load from localStorage
    // const stored = localStorage.getItem('results');
    // const results = stored ? JSON.parse(stored) : {};

    // Use useLocation to get the results passed from the previous page
    const location = useLocation();
    const [ isAnalyzing , setIsAnalyzing ] = React.useState(false);

    const results = location.state?.results;

    console.log("Results data---:", results);

    React.useEffect(() => {
        if (!results) {
            navigate('/'); // redirect to home if no results
        }
    }, [results, navigate]);

    if (!results) {
        return null; // Prevent rendering before redirect
    }

       
    // Deconstruct fields from the results object
    const {
        class_analysis,
        log_analysis,
        comprehensive_thread_analysis,
        customer_problem,
        problem_threads ,
        thread_analysis ,
    } = results;


    




    const handleDownloadReport = async () => {

        setIsAnalyzing(true);


        try {
          // Prepare the payload with the necessary fields
          const payload = {
            log_analysis,
            comprehensive_thread_analysis,
            customer_problem,
            class_analysis
          };
      
          // Send POST request to the backend to get the PDF
          const response = await fetch("http://127.0.0.1:8000/download_report", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
          });
      
          if (!response.ok) {
            throw new Error("Failed to download the report.");
          }
      
          // Receive the PDF as a blob and trigger download
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.setAttribute("download", "final_diagnostic_report.pdf");
          document.body.appendChild(link);
          link.click();
          link.parentNode.removeChild(link);
          window.URL.revokeObjectURL(url);
          setIsAnalyzing(false);
        } catch (error) {
          alert(error.message || "An error occurred while downloading the report.");
        }
      };

  return (
    <div id="report-content" className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-10">
          <div className="card shadow mb-5">
            <div className="card-header bg-orange text-white text-center d-flex align-items-center">
              <img
                src="/images/header_image.jpg" // Adjust image path as needed
                alt="Header Image"
                className="me-3"
                style={{ height: 100, width: 'auto' }}
              />
              <div>
                <h1 className="display-6">Analysis Results</h1>
                <p className="lead mb-0">Diagnostic report for your application</p>
              </div>
            </div>
            <div className="card-body">
              <div className="mb-4">
                <h3 className="h5">Customer Problem</h3>
                <div className="card bg-light">
                  <div className="card-body">
                    <p>{customer_problem}</p>
                  </div>
                </div>
              </div>

              {problem_threads && comprehensive_thread_analysis ==
               'Not applicable - no problematic threads identified.' && (
                <div className="mb-4">
                  <h3 className="h5">Thread Analysis</h3>
                  <div className="card bg-light">
                    <div className="card-body">
                      <pre className="mb-0">{thread_analysis}</pre>
                    </div>
                  </div>
                </div>
              )}

              {Array.isArray(problem_threads) && problem_threads.length > 0 && (
                <div className="mb-4">
                    <h3 className="h5">Problem Threads</h3>
                    <div className="card bg-light">
                    <div className="card-body">
                        <div>{problem_threads.join(', ')}</div>
                    </div>
                    </div>
                </div>
                )}

              {comprehensive_thread_analysis &&
               comprehensive_thread_analysis !==
               'Not applicable - no problematic threads identified.' && (
                <div className="mb-4">
                  <h3 className="h5">Comprehensive Thread Analysis</h3>
                  <div className="card bg-light">
                    <div className="card-body">
                      <pre className="mb-0">{comprehensive_thread_analysis}</pre>
                    </div>
                  </div>
                </div>
              )}

              {log_analysis &&
               log_analysis !== 'No log content available for analysis.' && (
                <div className="mb-4">
                  <h3 className="h5">Log Analysis</h3>
                  <div className="card bg-light">
                    <div className="card-body">
                      <pre className="mb-0">{log_analysis}</pre>
                    </div>
                  </div>
                </div>
              )}

              {class_analysis && (
                <div className="mb-4" >
                  <h3 className="h5">Class Analysis</h3>
                  <div className="card bg-light">
                    <div className="card-body">
                      <pre className="mb-0" >{class_analysis}</pre>
                    </div>
                  </div>
                </div>
              )}

            <div className="d-flex justify-content-end mt-4">
              <button 
                className={`btn btn-primary ${isAnalyzing ? 'loading' : ''}`} 
                onClick={handleDownloadReport}
                disabled={isAnalyzing}
              >
                {isAnalyzing && <span className="spinner-border" role="status" aria-hidden="true"></span>}
                {isAnalyzing ? 'Downloading...' : 'Download Full PDF Report'}
              </button>
            </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
