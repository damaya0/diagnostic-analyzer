import React from "react";
import "./styles.css"; // Adjust the path as necessary

// Props: error (string)
export default function Error({ error }) {
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card shadow">
            <div className="card-header bg-orange text-white text-center d-flex align-items-center">
              <img
                src="/static/images/header_image.jpg"
                alt="Header"
                className="me-3"
                style={{ height: "100px", width: "auto" }}
              />
              <div>
                <h1 className="display-6">Error</h1>
              </div>
            </div>
            <div className="card-body text-center">
              <p className="lead mb-4">{error}</p>
              <a href="/" className="btn btn-primary">
                Start a New Analysis
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
