// NotFound.jsx
import React from 'react';
import { Link } from 'react-router-dom';
import './styles.css';

export default function NotFoundPage() {
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card shadow text-center">
            <div className="card-header bg-orange text-white">
              <h2>404 - Page Not Found</h2>
            </div>
            <div className="card-body">
              <p className="lead mb-4">The page you are looking for does not exist.</p>
              <Link to="/" className="btn btn-primary">
                Go to Home
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
