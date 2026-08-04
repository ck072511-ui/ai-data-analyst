import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const UserRolesConsole = ({ token, showNotification }) => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);

  useEffect(() => {
    fetchUsersAndRoles();
  }, []);

  const fetchUsersAndRoles = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/users/roles`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data.users || []);
      setRoles(response.data.roles || []);
    } catch (error) {
      showNotification('Failed to load users list and roles', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    setUpdatingId(userId);
    try {
      await axios.patch(
        `${API_BASE_URL}/users/${userId}/role`,
        { role: newRole },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      showNotification('User role updated successfully', 'success');
      
      // Update state locally
      setUsers(prevUsers =>
        prevUsers.map(u => (u.id === userId ? { ...u, role: newRole } : u))
      );
    } catch (error) {
      showNotification(error.response?.data?.detail || 'Failed to update user role', 'error');
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="rbac-console-container animation-fade-in">
      <div className="rbac-console-card">
        <div className="console-header-bar">
          <h3>🔑 User Identity & Access Management</h3>
          <button className="refresh-btn" onClick={fetchUsersAndRoles} disabled={loading}>
            {loading ? 'Refreshing...' : '🔄 Refresh Log'}
          </button>
        </div>
        <p className="console-desc">
          Configure security policy boundaries by assigning user roles. Updates take effect immediately.
        </p>

        {loading && users.length === 0 ? (
          <div className="dashboard-skeleton-layout">
            <div className="skeleton-chart-card"></div>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="rbac-users-table">
              <thead>
                <tr>
                  <th>User Full Name</th>
                  <th>Email Address</th>
                  <th>Current Role</th>
                  <th>Assign New Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td>
                      <div className="rbac-user-name">
                        <span className="rbac-avatar">{u.full_name ? u.full_name[0].toUpperCase() : 'U'}</span>
                        <strong>{u.full_name || 'User'}</strong>
                      </div>
                    </td>
                    <td><code>{u.email}</code></td>
                    <td>
                      <span className={`role-pill-badge ${u.role.toLowerCase().replace(' ', '-')}`}>
                        {u.role}
                      </span>
                    </td>
                    <td>
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        disabled={updatingId === u.id}
                        className="rbac-role-select"
                      >
                        {roles.map(r => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <span className={`status-dot ${u.is_active ? 'active' : 'inactive'}`}>
                        {u.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserRolesConsole;
