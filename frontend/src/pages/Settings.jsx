import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const Settings = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [preferences, setPreferences] = useState(null);
  
  const [formData, setFormData] = useState({
    enabled_channels: [],
    target_keywords: [],
    industry: '',
    niche: '',
    exclude_keywords: [],
    scan_frequency: 'hourly',
    notification_channels: [],
    notification_email: '',
    notification_slack_webhook: '',
    notification_whatsapp_number: '',
    notify_on_high_score_only: true,
    min_score_for_notification: 70,
    min_opportunity_score: 50,
    enabled_opportunity_types: [],
    max_opportunities_per_day: 50,
    auto_generate_content: true,
    include_competitor_analysis: true,
    competitor_domains: [],
    // Lead Generation fields
    enable_lead_identification: true,
    product_name: '',
    product_description: '',
    target_customer_profile: '',
    key_problems_solved: [],
    buying_signals: [],
    competitive_advantages: [],
    min_lead_score: 40
  });
  
  const [keywordInput, setKeywordInput] = useState('');
  const [excludeKeywordInput, setExcludeKeywordInput] = useState('');
  const [competitorInput, setCompetitorInput] = useState('');
  const [problemInput, setProblemInput] = useState('');
  const [signalInput, setSignalInput] = useState('');
  const [advantageInput, setAdvantageInput] = useState('');

  useEffect(() => {
    fetchPreferences();
  }, []);

  const fetchPreferences = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }

      const response = await axios.get(`${API_URL}/api/preferences`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setPreferences(response.data);
      setFormData({
        enabled_channels: response.data.enabled_channels || [],
        target_keywords: response.data.target_keywords || [],
        industry: response.data.industry || '',
        niche: response.data.niche || '',
        exclude_keywords: response.data.exclude_keywords || [],
        scan_frequency: response.data.scan_frequency || 'hourly',
        notification_channels: response.data.notification_channels || [],
        notification_email: response.data.notification_email || '',
        notification_slack_webhook: response.data.notification_slack_webhook || '',
        notification_whatsapp_number: response.data.notification_whatsapp_number || '',
        notify_on_high_score_only: response.data.notify_on_high_score_only ?? true,
        min_score_for_notification: response.data.min_score_for_notification || 70,
        min_opportunity_score: response.data.min_opportunity_score || 50,
        enabled_opportunity_types: response.data.enabled_opportunity_types || [],
        max_opportunities_per_day: response.data.max_opportunities_per_day || 50,
        auto_generate_content: response.data.auto_generate_content ?? true,
        include_competitor_analysis: response.data.include_competitor_analysis ?? true,
        competitor_domains: response.data.competitor_domains || [],
        // Lead Generation fields
        enable_lead_identification: response.data.enable_lead_identification ?? true,
        product_name: response.data.product_name || '',
        product_description: response.data.product_description || '',
        target_customer_profile: response.data.target_customer_profile || '',
        key_problems_solved: response.data.key_problems_solved || [],
        buying_signals: response.data.buying_signals || [],
        competitive_advantages: response.data.competitive_advantages || [],
        min_lead_score: response.data.min_lead_score || 40
      });
      setLoading(false);
    } catch (error) {
      console.error('Error fetching preferences:', error);
      if (error.response?.status === 401) {
        navigate('/login');
      }
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    
    try {
      const token = localStorage.getItem('token');
      const response = await axios.put(
        `${API_URL}/api/preferences`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setMessage('Settings saved successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Error saving settings. Please try again.');
      console.error('Error saving preferences:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Are you sure you want to reset all settings to defaults?')) {
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_URL}/api/preferences/reset`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setMessage('Settings reset to defaults!');
      fetchPreferences();
    } catch (error) {
      setMessage('Error resetting settings.');
      console.error('Error resetting preferences:', error);
    }
  };

  const toggleChannel = (channel) => {
    setFormData(prev => ({
      ...prev,
      enabled_channels: prev.enabled_channels.includes(channel)
        ? prev.enabled_channels.filter(c => c !== channel)
        : [...prev.enabled_channels, channel]
    }));
  };

  const toggleOpportunityType = (type) => {
    setFormData(prev => ({
      ...prev,
      enabled_opportunity_types: prev.enabled_opportunity_types.includes(type)
        ? prev.enabled_opportunity_types.filter(t => t !== type)
        : [...prev.enabled_opportunity_types, type]
    }));
  };

  const toggleNotificationChannel = (channel) => {
    setFormData(prev => ({
      ...prev,
      notification_channels: prev.notification_channels.includes(channel)
        ? prev.notification_channels.filter(c => c !== channel)
        : [...prev.notification_channels, channel]
    }));
  };

  const addKeyword = () => {
    if (keywordInput.trim()) {
      setFormData(prev => ({
        ...prev,
        target_keywords: [...prev.target_keywords, keywordInput.trim()]
      }));
      setKeywordInput('');
    }
  };

  const removeKeyword = (keyword) => {
    setFormData(prev => ({
      ...prev,
      target_keywords: prev.target_keywords.filter(k => k !== keyword)
    }));
  };

  const addExcludeKeyword = () => {
    if (excludeKeywordInput.trim()) {
      setFormData(prev => ({
        ...prev,
        exclude_keywords: [...prev.exclude_keywords, excludeKeywordInput.trim()]
      }));
      setExcludeKeywordInput('');
    }
  };

  const removeExcludeKeyword = (keyword) => {
    setFormData(prev => ({
      ...prev,
      exclude_keywords: prev.exclude_keywords.filter(k => k !== keyword)
    }));
  };

  const addCompetitor = () => {
    if (competitorInput.trim()) {
      setFormData(prev => ({
        ...prev,
        competitor_domains: [...prev.competitor_domains, competitorInput.trim()]
      }));
      setCompetitorInput('');
    }
  };

  const removeCompetitor = (domain) => {
    setFormData(prev => ({
      ...prev,
      competitor_domains: prev.competitor_domains.filter(d => d !== domain)
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-lg">Loading settings...</div>
      </div>
    );
  }

  const channels = [
    { value: 'reddit', label: 'Reddit' },
    { value: 'quora', label: 'Quora' },
    { value: 'twitter', label: 'Twitter/X' },
    { value: 'linkedin', label: 'LinkedIn' },
    { value: 'facebook', label: 'Facebook Groups' },
    { value: 'product_hunt', label: 'Product Hunt' },
    { value: 'hacker_news', label: 'Hacker News' },
    { value: 'google_trends', label: 'Google Trends' },
    { value: 'youtube', label: 'YouTube' },
    { value: 'competitor', label: 'Competitor Monitoring' },
    { value: 'forum', label: 'Forums' }
  ];

  const opportunityTypes = [
    { value: 'question', label: 'Questions' },
    { value: 'trending_keyword', label: 'Trending Keywords' },
    { value: 'competitor_mention', label: 'Competitor Mentions' },
    { value: 'complaint', label: 'Complaints' },
    { value: 'forum_discussion', label: 'Forum Discussions' },
    { value: 'content_gap', label: 'Content Gaps' }
  ];

  const scanFrequencies = [
    { value: 'hourly', label: 'Every Hour' },
    { value: 'twice_daily', label: 'Twice Daily' },
    { value: 'daily', label: 'Once Daily' },
    { value: 'weekly', label: 'Weekly' }
  ];

  const notificationChannels = [
    { value: 'email', label: 'Email' },
    { value: 'slack', label: 'Slack' },
    { value: 'whatsapp', label: 'WhatsApp' },
    { value: 'none', label: 'None' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-5xl mx-auto px-4">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-600 mt-1">Customize your traffic opportunity preferences</p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Back to Dashboard
          </button>
        </div>

        {message && (
          <div className={`mb-6 p-4 rounded-lg ${message.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
            {message}
          </div>
        )}

        <div className="space-y-6">
          {/* Channel Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">📡 Channel Selection</h2>
            <p className="text-gray-600 mb-4">Choose which platforms to scan for opportunities</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {channels.map(channel => (
                <label key={channel.value} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.enabled_channels.includes(channel.value)}
                    onChange={() => toggleChannel(channel.value)}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-gray-700">{channel.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Topic & Keywords */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">🎯 Topic & Keywords</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Industry</label>
                <input
                  type="text"
                  value={formData.industry}
                  onChange={(e) => setFormData({...formData, industry: e.target.value})}
                  placeholder="e.g., SaaS, B2B Marketing"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Niche</label>
                <input
                  type="text"
                  value={formData.niche}
                  onChange={(e) => setFormData({...formData, niche: e.target.value})}
                  placeholder="e.g., Email tools, Lead generation"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Target Keywords</label>
                <div className="flex space-x-2 mb-2">
                  <input
                    type="text"
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
                    placeholder="Add keyword..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={addKeyword}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {formData.target_keywords.map((keyword, index) => (
                    <span key={index} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm flex items-center space-x-1">
                      <span>{keyword}</span>
                      <button onClick={() => removeKeyword(keyword)} className="text-blue-600 hover:text-blue-800">×</button>
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Exclude Keywords</label>
                <div className="flex space-x-2 mb-2">
                  <input
                    type="text"
                    value={excludeKeywordInput}
                    onChange={(e) => setExcludeKeywordInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addExcludeKeyword()}
                    placeholder="Add keyword to exclude..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={addExcludeKeyword}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                  >
                    Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {formData.exclude_keywords.map((keyword, index) => (
                    <span key={index} className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm flex items-center space-x-1">
                      <span>{keyword}</span>
                      <button onClick={() => removeExcludeKeyword(keyword)} className="text-red-600 hover:text-red-800">×</button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Smart Keyword Discovery */}
          <SmartKeywordDiscovery 
            onKeywordsExtracted={(keywords, metadata) => {
              setFormData(prev => ({
                ...prev,
                target_keywords: [...new Set([...prev.target_keywords, ...keywords])]
              }));
            }}
          />

          {/* Scan Frequency */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">⏰ Scan Frequency</h2>
            <select
              value={formData.scan_frequency}
              onChange={(e) => setFormData({...formData, scan_frequency: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {scanFrequencies.map(freq => (
                <option key={freq.value} value={freq.value}>{freq.label}</option>
              ))}
            </select>
          </div>

          {/* Notifications */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">🔔 Notifications</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Notification Channels</label>
                <div className="flex flex-wrap gap-3">
                  {notificationChannels.map(channel => (
                    <label key={channel.value} className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.notification_channels.includes(channel.value)}
                        onChange={() => toggleNotificationChannel(channel.value)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <span className="text-gray-700">{channel.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {formData.notification_channels.includes('email') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Notification Email</label>
                  <input
                    type="email"
                    value={formData.notification_email}
                    onChange={(e) => setFormData({...formData, notification_email: e.target.value})}
                    placeholder="your@email.com"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}

              {formData.notification_channels.includes('slack') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Slack Webhook URL</label>
                  <input
                    type="text"
                    value={formData.notification_slack_webhook}
                    onChange={(e) => setFormData({...formData, notification_slack_webhook: e.target.value})}
                    placeholder="https://hooks.slack.com/services/..."
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}

              {formData.notification_channels.includes('whatsapp') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">WhatsApp Number</label>
                  <input
                    type="text"
                    value={formData.notification_whatsapp_number}
                    onChange={(e) => setFormData({...formData, notification_whatsapp_number: e.target.value})}
                    placeholder="+1234567890"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.notify_on_high_score_only}
                  onChange={(e) => setFormData({...formData, notify_on_high_score_only: e.target.checked})}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <label className="text-gray-700">Only notify for high-priority opportunities</label>
              </div>

              {formData.notify_on_high_score_only && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Minimum Score for Notification: {formData.min_score_for_notification}
                  </label>
                  <input
                    type="range"
                    min="50"
                    max="100"
                    value={formData.min_score_for_notification}
                    onChange={(e) => setFormData({...formData, min_score_for_notification: parseInt(e.target.value)})}
                    className="w-full"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Opportunity Filters */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">🎛️ Opportunity Filters</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Opportunity Score: {formData.min_opportunity_score}
                </label>
                <input
                  type="range"
                  min="30"
                  max="100"
                  value={formData.min_opportunity_score}
                  onChange={(e) => setFormData({...formData, min_opportunity_score: parseInt(e.target.value)})}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Opportunities Per Day: {formData.max_opportunities_per_day}
                </label>
                <input
                  type="range"
                  min="5"
                  max="100"
                  value={formData.max_opportunities_per_day}
                  onChange={(e) => setFormData({...formData, max_opportunities_per_day: parseInt(e.target.value)})}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Opportunity Types</label>
                <div className="grid grid-cols-2 gap-3">
                  {opportunityTypes.map(type => (
                    <label key={type.value} className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.enabled_opportunity_types.includes(type.value)}
                        onChange={() => toggleOpportunityType(type.value)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <span className="text-gray-700">{type.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">⚙️ Advanced Settings</h2>
            
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.auto_generate_content}
                  onChange={(e) => setFormData({...formData, auto_generate_content: e.target.checked})}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <label className="text-gray-700">Auto-generate content templates</label>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.include_competitor_analysis}
                  onChange={(e) => setFormData({...formData, include_competitor_analysis: e.target.checked})}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <label className="text-gray-700">Include competitor analysis</label>
              </div>

              {formData.include_competitor_analysis && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Competitor Domains</label>
                  <div className="flex space-x-2 mb-2">
                    <input
                      type="text"
                      value={competitorInput}
                      onChange={(e) => setCompetitorInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && addCompetitor()}
                      placeholder="e.g., apollo.io"
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={addCompetitor}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {formData.competitor_domains.map((domain, index) => (
                      <span key={index} className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm flex items-center space-x-1">
                        <span>{domain}</span>
                        <button onClick={() => removeCompetitor(domain)} className="text-purple-600 hover:text-purple-800">×</button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-between">
            <button
              onClick={handleReset}
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Reset to Defaults
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Smart Keyword Discovery Component
const SmartKeywordDiscovery = ({ onKeywordsExtracted }) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [seoData, setSeoData] = useState(null);
  const [selectedKeywords, setSelectedKeywords] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleExtractKeywords = async () => {
    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    setLoading(true);
    setError('');
    setExtractedData(null);
    setSeoData(null);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/extract-keywords`,
        { url: url.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        setExtractedData(response.data);
        setSelectedKeywords(response.data.keywords || []);
        setSuccess('Keywords extracted successfully!');
        setTimeout(() => setSuccess(''), 3000);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to extract keywords');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeSEO = async () => {
    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    setAnalyzing(true);
    setError('');
    setSeoData(null);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/analyze-seo`,
        { url: url.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        setSeoData(response.data);
        setSuccess('SEO analysis completed!');
        setTimeout(() => setSuccess(''), 3000);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze SEO');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleApproveKeywords = async () => {
    if (selectedKeywords.length === 0) {
      setError('No keywords selected');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_URL}/api/save-extracted-keywords`,
        {
          keywords: selectedKeywords,
          url: url,
          metadata: {
            industry: extractedData?.industry,
            niche: extractedData?.niche,
            business_type: extractedData?.business_type
          }
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      onKeywordsExtracted(selectedKeywords, {
        industry: extractedData?.industry,
        niche: extractedData?.niche
      });

      setSuccess(`Added ${selectedKeywords.length} keywords to your preferences!`);
      setTimeout(() => {
        setSuccess('');
        setExtractedData(null);
        setUrl('');
        setSelectedKeywords([]);
      }, 2000);
    } catch (err) {
      setError('Failed to save keywords');
    }
  };

  const toggleKeyword = (keyword) => {
    setSelectedKeywords(prev =>
      prev.includes(keyword)
        ? prev.filter(k => k !== keyword)
        : [...prev, keyword]
    );
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-900">🚀 Smart Keyword Discovery</h2>
      <p className="text-gray-600 mb-4">
        Automatically extract keywords from your website, social profiles, or competitor URLs
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-100 text-green-700 rounded-lg">
          {success}
        </div>
      )}

      <div className="space-y-4">
        {/* URL Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Website or Social Media URL
          </label>
          <div className="flex space-x-2">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com or instagram.com/username"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleExtractKeywords}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
            >
              {loading ? 'Extracting...' : 'Extract Keywords'}
            </button>
            <button
              onClick={handleAnalyzeSEO}
              disabled={analyzing}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 whitespace-nowrap"
            >
              {analyzing ? 'Analyzing...' : 'SEO Analysis'}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Supports: Websites, Instagram, LinkedIn, Facebook, Twitter, YouTube
          </p>
        </div>

        {/* Extracted Keywords */}
        {extractedData && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <h3 className="font-semibold text-gray-900 mb-3">Extracted Keywords ({extractedData.keywords?.length || 0})</h3>
            
            {extractedData.industry && (
              <p className="text-sm text-gray-600 mb-2">
                <strong>Industry:</strong> {extractedData.industry}
              </p>
            )}
            
            {extractedData.niche && (
              <p className="text-sm text-gray-600 mb-2">
                <strong>Niche:</strong> {extractedData.niche}
              </p>
            )}

            {extractedData.business_type && (
              <p className="text-sm text-gray-600 mb-3">
                <strong>Type:</strong> {extractedData.business_type}
              </p>
            )}

            <div className="flex flex-wrap gap-2 mb-4">
              {extractedData.keywords?.map((keyword, index) => (
                <label
                  key={index}
                  className={`px-3 py-1 rounded-full text-sm cursor-pointer transition-colors ${
                    selectedKeywords.includes(keyword)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedKeywords.includes(keyword)}
                    onChange={() => toggleKeyword(keyword)}
                    className="hidden"
                  />
                  {keyword}
                </label>
              ))}
            </div>

            <button
              onClick={handleApproveKeywords}
              disabled={selectedKeywords.length === 0}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              Add {selectedKeywords.length} Selected Keywords
            </button>
          </div>
        )}

        {/* SEO Analysis Results */}
        {seoData && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold text-gray-900">SEO Analysis</h3>
              <div className="text-2xl font-bold text-blue-600">
                {seoData.seo_score}/100
              </div>
            </div>

            {/* Issues */}
            {seoData.issues?.length > 0 && (
              <div className="mb-3">
                <h4 className="text-sm font-semibold text-red-700 mb-2">🔴 Critical Issues</h4>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {seoData.issues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warnings */}
            {seoData.warnings?.length > 0 && (
              <div className="mb-3">
                <h4 className="text-sm font-semibold text-yellow-700 mb-2">⚠️ Warnings</h4>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {seoData.warnings.map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Good Practices */}
            {seoData.good_practices?.length > 0 && (
              <div className="mb-3">
                <h4 className="text-sm font-semibold text-green-700 mb-2">✅ Good Practices</h4>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {seoData.good_practices.map((practice, i) => (
                    <li key={i}>{practice}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Traffic Strategies */}
            {seoData.traffic_strategies?.length > 0 && (
              <div className="mb-3">
                <h4 className="text-sm font-semibold text-purple-700 mb-2">📈 Traffic Growth Strategies</h4>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {seoData.traffic_strategies.map((strategy, i) => (
                    <li key={i}>{strategy}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Keyword Opportunities */}
            {seoData.keyword_opportunities?.length > 0 && (
              <div className="mb-3">
                <h4 className="text-sm font-semibold text-blue-700 mb-2">🔑 Keyword Opportunities</h4>
                <div className="flex flex-wrap gap-2">
                  {seoData.keyword_opportunities.map((keyword, i) => (
                    <span key={i} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Content Suggestions */}
            {seoData.content_suggestions?.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-indigo-700 mb-2">💡 Content Suggestions</h4>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {seoData.content_suggestions.map((suggestion, i) => (
                    <li key={i}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;
