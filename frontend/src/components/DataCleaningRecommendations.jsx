import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const DataCleaningRecommendations = ({ token, datasetId, showNotification, onApplyRecommendation }) => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (datasetId) {
      fetchRecommendations();
    }
  }, [datasetId]);

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/datasets/${datasetId}/recommendations`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRecommendations(response.data);
    } catch (error) {
      showNotification('Failed to fetch recommendations', 'error');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceClass = (score) => {
    if (score >= 90) return 'excellent';
    if (score >= 80) return 'good';
    return 'average';
  };

  if (loading) {
    return (
      <div className="preview-skeleton-loader">
        <div className="skeleton-row short"></div>
        <div className="skeleton-row mt-15"></div>
        <div className="skeleton-row"></div>
      </div>
    );
  }

  if (recommendations.length === 0) {
    return (
      <div className="preview-empty-report">
        <span className="radar-icon">🎉</span>
        <h5>No Issues Detected</h5>
        <p>Excellent! The recommendation engine analyzed the dataset profile and found no critical missing values, duplicates, mixed types, or constant features.</p>
      </div>
    );
  }

  return (
    <div className="recommendations-container animation-fade-in">
      <div className="recommendations-header">
        <h4>💡 Heuristic Cleaning Recommendations</h4>
        <p>Our rule-based engine detected the following issues. Review recommendations and apply them to the checklist configuration.</p>
      </div>
      
      <div className="recommendations-grid">
        {recommendations.map((rec, index) => (
          <div key={index} className="recommendation-card">
            <div className="card-header">
              <span className={`confidence-badge ${getConfidenceClass(rec.confidence_score)}`}>
                {rec.confidence_score}% Confidence
              </span>
              <h5>{rec.recommendation}</h5>
            </div>
            
            <div className="card-body">
              <p className="rec-issue"><strong>Detected Issue:</strong> {rec.issue}</p>
              <p className="rec-reason"><strong>Reasoning:</strong> {rec.reason}</p>
              <p className="rec-impact"><strong>Expected Impact:</strong> {rec.expected_impact}</p>
            </div>
            
            <div className="card-footer">
              <button 
                className="apply-rec-btn"
                onClick={() => {
                  if (onApplyRecommendation) {
                    onApplyRecommendation(rec);
                  }
                }}
              >
                ⚡ Populate Configuration
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DataCleaningRecommendations;
