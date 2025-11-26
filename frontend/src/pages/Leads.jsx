import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';

const Leads = () => {
  const navigate = useNavigate();
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState({ status: '', quality: '' });
  const [selectedLead, setSelectedLead] = useState(null);
  const [contactNotes, setContactNotes] = useState('');
  const [identifying, setIdentifying] = useState(false);

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [filter]);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filter.status) params.append('status', filter.status);
      if (filter.quality) params.append('quality', filter.quality);
      
      const response = await api.get(`/leads?${params.toString()}`);
      setLeads(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching leads:', err);
      setError('Failed to load leads');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/leads/stats');
      setStats(response.data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  const handleMarkContacted = async (leadId) => {
    try {
      await api.post(`/leads/${leadId}/contact`, {
        contact_notes: contactNotes
      });
      setContactNotes('');
      setSelectedLead(null);
      fetchLeads();
      fetchStats();
    } catch (err) {
      console.error('Error marking lead as contacted:', err);
      alert('Failed to update lead');
    }
  };

  const handleUpdateStatus = async (leadId, newStatus) => {
    try {
      await api.put(`/leads/${leadId}`, { status: newStatus });
      fetchLeads();
      fetchStats();
    } catch (err) {
      console.error('Error updating lead:', err);
      alert('Failed to update lead');
    }
  };

  const handleDeleteLead = async (leadId) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;
    
    try {
      await api.delete(`/leads/${leadId}`);
      fetchLeads();
      fetchStats();
    } catch (err) {
      console.error('Error deleting lead:', err);
      alert('Failed to delete lead');
    }
  };

  const handleIdentifyLeads = async () => {
    try {
      setIdentifying(true);
      await api.post('/leads/identify');
      alert('Lead identification started! This may take a few minutes. Refresh the page to see new leads.');
    } catch (err) {
      console.error('Error triggering lead identification:', err);
      alert('Failed to start lead identification. Please try again.');
    } finally {
      setIdentifying(false);
    }
  };

  const getQualityColor = (quality) => {
    switch (quality) {
      case 'hot': return 'bg-red-100 text-red-800';
      case 'warm': return 'bg-orange-100 text-orange-800';
      case 'cold': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'new': return 'bg-green-100 text-green-800';
      case 'contacted': return 'bg-blue-100 text-blue-800';
      case 'qualified': return 'bg-purple-100 text-purple-800';
      case 'not_interested': return 'bg-gray-100 text-gray-800';
      case 'converted': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">LinkedIn Leads</h1>
              <p className="mt-1 text-sm text-gray-600">
                Potential customers identified from LinkedIn posts and comments
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleIdentifyLeads}
                disabled={identifying}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {identifying ? 'Identifying...' : 'Find New Leads'}
              </button>
              <button
                onClick={() => navigate('/dashboard')}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-sm text-gray-600">Total Leads</div>
              <div className="text-2xl font-bold text-gray-900">{stats.total_leads}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-sm text-gray-600">New</div>
              <div className="text-2xl font-bold text-green-600">{stats.by_status.new}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-sm text-gray-600">Contacted</div>
              <div className="text-2xl font-bold text-blue-600">{stats.by_status.contacted}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-sm text-gray-600">Hot Leads</div>
              <div className="text-2xl font-bold text-red-600">{stats.by_quality.hot}</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white p-4 rounded-lg shadow mb-6">
          <div className="flex gap-4 items-center">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filter.status}
                onChange={(e) => setFilter({ ...filter, status: e.target.value })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="qualified">Qualified</option>
                <option value="not_interested">Not Interested</option>
                <option value="converted">Converted</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quality</label>
              <select
                value={filter.quality}
                onChange={(e) => setFilter({ ...filter, quality: e.target.value })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="hot">Hot</option>
                <option value="warm">Warm</option>
                <option value="cold">Cold</option>
              </select>
            </div>
            <button
              onClick={() => setFilter({ status: '', quality: '' })}
              className="mt-6 px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              Clear Filters
            </button>
          </div>
        </div>

        {/* Leads List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading leads...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 p-4 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        ) : leads.length === 0 ? (
          <div className="bg-white p-12 rounded-lg shadow text-center">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No leads yet</h3>
            <p className="text-gray-600 mb-6">
              Click "Find New Leads" to start identifying potential customers from LinkedIn
            </p>
            <button
              onClick={handleIdentifyLeads}
              disabled={identifying}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Find New Leads
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {leads.map((lead) => (
              <div key={lead.id} className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {lead.name || 'Unknown'}
                      </h3>
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getQualityColor(lead.quality_score)}`}>
                        {lead.quality_score.toUpperCase()}
                      </span>
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(lead.status)}`}>
                        {lead.status.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">
                        Score: {lead.score}/100
                      </span>
                    </div>
                    {lead.linkedin_url && lead.linkedin_url !== 'N/A' && (
                      <a
                        href={lead.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline"
                      >
                        View LinkedIn Profile →
                      </a>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {lead.status === 'new' && (
                      <button
                        onClick={() => setSelectedLead(lead)}
                        className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Mark Contacted
                      </button>
                    )}
                    <select
                      value={lead.status}
                      onChange={(e) => handleUpdateStatus(lead.id, e.target.value)}
                      className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="new">New</option>
                      <option value="contacted">Contacted</option>
                      <option value="qualified">Qualified</option>
                      <option value="not_interested">Not Interested</option>
                      <option value="converted">Converted</option>
                    </select>
                    <button
                      onClick={() => handleDeleteLead(lead.id)}
                      className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-1">Need Identified:</p>
                    <p className="text-sm text-gray-600">{lead.need_identified}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-1">Qualification Reason:</p>
                    <p className="text-sm text-gray-600">{lead.reason_qualified}</p>
                  </div>
                </div>

                {lead.suggested_approach && (
                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-1">Suggested Approach:</p>
                    <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded">
                      {lead.suggested_approach}
                    </p>
                  </div>
                )}

                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-1">Comment/Post:</p>
                  <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                    {lead.comment_text}
                  </p>
                </div>

                {lead.post_url && (
                  <a
                    href={lead.post_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:underline"
                  >
                    View Original Post →
                  </a>
                )}

                {lead.keywords_matched && lead.keywords_matched.length > 0 && (
                  <div className="mt-3 flex gap-2">
                    <span className="text-xs text-gray-500">Keywords:</span>
                    {lead.keywords_matched.map((keyword, idx) => (
                      <span key={idx} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                        {keyword}
                      </span>
                    ))}
                  </div>
                )}

                {lead.contact_notes && (
                  <div className="mt-3 border-t pt-3">
                    <p className="text-sm font-medium text-gray-700 mb-1">Contact Notes:</p>
                    <p className="text-sm text-gray-600">{lead.contact_notes}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Contact Modal */}
        {selectedLead && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Mark Lead as Contacted
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Add notes about your conversation with {selectedLead.name || 'this lead'}
              </p>
              <textarea
                value={contactNotes}
                onChange={(e) => setContactNotes(e.target.value)}
                placeholder="Add your contact notes here..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
                rows="4"
              />
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setSelectedLead(null);
                    setContactNotes('');
                  }}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleMarkContacted(selectedLead.id)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Save & Mark Contacted
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Leads;
