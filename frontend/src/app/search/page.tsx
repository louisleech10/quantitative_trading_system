// frontend/src/app/search/page.tsx
// Diagnostic version with detailed API response logging

'use client';

import { useEffect, useState } from 'react';

interface ApiStatus {
  connected: boolean;
  templates: any[];
  error?: string;
  rawResponse?: any;
}

export default function SearchPage() {
  const [mounted, setMounted] = useState(false);
  const [apiStatus, setApiStatus] = useState<ApiStatus>({
    connected: false,
    templates: []
  });
  const [isTestingConnection, setIsTestingConnection] = useState(false);

  useEffect(() => {
    setMounted(true);
    testApiConnection();
  }, []);

  const testApiConnection = async () => {
    setIsTestingConnection(true);
    try {
      console.log('Testing health endpoint...');
      const healthResponse = await fetch('http://localhost:8000/health');
      console.log('Health response status:', healthResponse.status);
      
      if (healthResponse.ok) {
        console.log('Testing templates endpoint...');
        const templatesResponse = await fetch('http://localhost:8000/api/v1/config/templates');
        console.log('Templates response status:', templatesResponse.status);
        
        const templatesData = await templatesResponse.json();
        console.log('Templates raw response:', templatesData);
        
        setApiStatus({
          connected: true,
          templates: templatesData.data?.templates || [],
          error: undefined,
          rawResponse: templatesData
        });
      } else {
        throw new Error(`Health check failed with status: ${healthResponse.status}`);
      }
    } catch (error) {
      console.error('API connection error:', error);
      setApiStatus({
        connected: false,
        templates: [],
        error: error instanceof Error ? error.message : 'Connection failed'
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const executeSearch = async (template: any) => {
    try {
      console.log('Starting search with template:', template);
      const response = await fetch('http://localhost:8000/api/v1/search/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          config: template.config
        }),
      });

      const result = await response.json();
      console.log('Search result:', result);
      
      if (result.success) {
        alert(`Search started! Task ID: ${result.data.task_id}`);
      } else {
        alert(`Search failed: ${result.error?.message}`);
      }
    } catch (error) {
      console.error('Search error:', error);
      alert('Search request failed');
    }
  };

  if (!mounted) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Case Search System
          </h1>
          <p className="mt-2 text-gray-600">
            Search and analyze cryptocurrency trading cases
          </p>
        </div>

        {/* Connection Status */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">System Status</h2>
            <button
              onClick={testApiConnection}
              disabled={isTestingConnection}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {isTestingConnection ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <span>Frontend: Ready</span>
            </div>
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-3 ${
                apiStatus.connected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span>Backend API: {apiStatus.connected ? 'Connected' : 'Disconnected'}</span>
              {apiStatus.error && (
                <span className="ml-2 text-sm text-red-600">({apiStatus.error})</span>
              )}
            </div>
          </div>
        </div>

        {/* Debug Information */}
        {apiStatus.connected && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Debug Information</h2>
            <div className="space-y-2 text-sm">
              <div>
                <strong>Templates Array Length:</strong> {apiStatus.templates.length}
              </div>
              <div>
                <strong>Raw API Response:</strong>
                <pre className="mt-2 bg-gray-100 p-3 rounded text-xs overflow-auto max-h-40">
                  {JSON.stringify(apiStatus.rawResponse, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* Templates Section */}
        {apiStatus.connected && apiStatus.templates.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Available Search Templates</h2>
            <div className="grid gap-4">
              {apiStatus.templates.map((template: any) => (
                <div key={template.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium">{template.name}</h3>
                      <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                      <div className="text-xs text-gray-500 mt-2">
                        Timeframe: {template.config?.timeframe} | 
                        Sample Limit: {template.config?.sample_limit} | 
                        Period: {template.config?.start_date} to {template.config?.end_date}
                      </div>
                    </div>
                    <button
                      onClick={() => executeSearch(template)}
                      className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                    >
                      Start Search
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            Next Steps 📋
          </h3>
          <div className="text-blue-700">
            {!apiStatus.connected ? (
              <div>
                <p className="mb-2">Please ensure your FastAPI backend is running:</p>
                <code className="bg-blue-100 px-2 py-1 rounded text-sm">
                  python run_api.py
                </code>
              </div>
            ) : (
              <div>
                <p className="mb-2">✅ Backend connected! Check console (F12) for debug info.</p>
                <p className="text-sm">If no templates show above, check the Debug Information section.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}