import React from 'react';

const UnauthorizedPage = ({ requiredPermission, onBack }) => {
  return (
    <div className="unauthorized-page-container animation-fade-in">
      <div className="unauthorized-card">
        <div className="unauthorized-icon-shield">🔒</div>
        <h2>Access Restricted</h2>
        <p className="unauthorized-msg">
          You do not have the required permissions to access this feature.
        </p>
        {requiredPermission && (
          <div className="permission-badge-needed">
            Required Permission: <code>{requiredPermission}</code>
          </div>
        )}
        <p className="contact-admin-msg">
          Please contact your administrator to upgrade your access level.
        </p>
        <button className="back-safety-btn" onClick={onBack}>
          ⬅ Back to Safety
        </button>
      </div>
    </div>
  );
};

export default UnauthorizedPage;
