import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import { Database, Upload, Play, Server, LineChart, FileJson } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Dataset {
  name: string;
  physicalName: string;
  path: string;
}

function App() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [query, setQuery] = useState("SELECT category, SUM(sales) as total_sales FROM sample_sales GROUP BY category");
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState<'notebook' | 'chart'>('notebook');

  const fetchDatasets = async () => {
    try {
      const res = await axios.get('/api/v1/catalog/datasets');
      setDatasets(res.data);
    } catch (e) {
      console.error("Failed to fetch datasets", e);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);
    try {
      await axios.post('/api/v1/upload', formData);
      fetchDatasets();
    } catch (e: any) {
      alert("Failed to upload: " + (e.response?.data?.detail || "Error"));
    } finally {
      setUploading(false);
    }
  };

  const handleRunQuery = async () => {
    setLoading(true);
    setError(null);
    setResults(null);

    // Naive way to extract tables used in query for our backend
    const usedDatasets = datasets.filter(d => query.includes(d.name)).map(d => d.name);

    try {
      const res = await axios.post('/api/v1/query/execute', {
        query: query,
        datasets_used: usedDatasets
      });
      setResults(res.data.result);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const renderTable = () => {
    if (!results || !results.data || results.data.length === 0) return <div>No data</div>;
    const cols = Object.keys(results.data[0]);

    return (
      <div className="overflow-x-auto border border-gray-200 rounded-md">
        <table className="min-w-full divide-y divide-gray-200 text-sm text-left">
          <thead className="bg-gray-50">
            <tr>
              {cols.map((col, i) => (
                <th key={i} className="px-4 py-2 font-semibold text-gray-700">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {results.data.map((row: any, i: number) => (
              <tr key={i} className="hover:bg-gray-50">
                {cols.map((col, j) => (
                  <td key={j} className="px-4 py-2 text-gray-600 whitespace-nowrap">{String(row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderChart = () => {
    if (!results || !results.data || results.data.length === 0) return <div className="p-4 text-gray-500">Run a query with numeric results to visualize.</div>;
    const cols = Object.keys(results.data[0]);

    // Guess X and Y axes (first string for X, first number for Y)
    const xAxisCol = cols[0];
    const yAxisCol = cols.length > 1 ? cols[1] : cols[0];

    return (
      <div className="h-96 w-full p-4 bg-white border border-gray-200 rounded shadow-sm">
        <h3 className="text-lg font-semibold mb-4 text-gray-700">Auto-Generated Chart (Superset-Lite)</h3>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={results.data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xAxisCol} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey={yAxisCol} fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-800">
      {/* Sidebar - Marquez Catalog Proxy */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col shadow-sm z-10">
        <div className="p-4 border-b border-gray-200 flex items-center space-x-2">
          <Server className="w-6 h-6 text-blue-600" />
          <h1 className="text-xl font-bold tracking-tight text-gray-800">PondHouse</h1>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Marquez Catalog</h2>
          <ul className="space-y-2">
            {datasets.map((d, i) => (
              <li key={i} className="flex items-center text-sm p-2 hover:bg-blue-50 rounded text-gray-700 cursor-pointer transition">
                <Database className="w-4 h-4 mr-2 text-blue-500" />
                {d.name}
              </li>
            ))}
            {datasets.length === 0 && <p className="text-xs text-gray-400 italic">No datasets registered.</p>}
          </ul>
        </div>

        <div className="p-4 border-t border-gray-200">
          <label className="flex items-center justify-center w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md cursor-pointer hover:bg-blue-700 transition shadow-sm">
            <Upload className="w-4 h-4 mr-2" />
            {uploading ? "Uploading..." : "Upload File"}
            <input type="file" className="hidden" accept=".csv,.parquet" onChange={handleUpload} disabled={uploading} />
          </label>
        </div>
      </div>

      {/* Main Content - Workspace */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header Tabs */}
        <div className="bg-white border-b border-gray-200 px-6 py-3 flex space-x-4">
           <button
             onClick={() => setActiveTab('notebook')}
             className={`flex items-center space-x-2 px-3 py-2 rounded transition ${activeTab === 'notebook' ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}>
             <FileJson className="w-4 h-4" />
             <span>Notebook (SQL)</span>
           </button>
           <button
             onClick={() => setActiveTab('chart')}
             className={`flex items-center space-x-2 px-3 py-2 rounded transition ${activeTab === 'chart' ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}>
             <LineChart className="w-4 h-4" />
             <span>Dashboard</span>
           </button>
        </div>

        {/* Editor Area */}
        {activeTab === 'notebook' && (
          <div className="flex-1 flex flex-col p-6 space-y-4 overflow-y-auto">
            <div className="flex justify-between items-center">
               <h2 className="text-lg font-semibold text-gray-800">Workspace</h2>
               <button
                 onClick={handleRunQuery}
                 disabled={loading}
                 className="flex items-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 transition shadow-sm">
                 <Play className="w-4 h-4 mr-2" />
                 {loading ? "Running via SmallPond..." : "Run Query"}
               </button>
            </div>

            <div className="border border-gray-300 rounded overflow-hidden shadow-sm h-64 bg-white">
              <Editor
                height="100%"
                defaultLanguage="sql"
                theme="vs-light"
                value={query}
                onChange={(val) => setQuery(val || "")}
                options={{ minimap: { enabled: false }, fontSize: 14 }}
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded shadow-sm">
                <strong>Error: </strong> {error}
              </div>
            )}

            {/* Results Table */}
            {results && !error && (
              <div className="mt-6 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                   <h3 className="font-semibold text-gray-700">Results</h3>
                   <span className="text-xs text-gray-500">{results.row_count} rows fetched from DuckDB</span>
                </div>
                {renderTable()}
              </div>
            )}
          </div>
        )}

        {/* Chart Area */}
        {activeTab === 'chart' && (
           <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
              {renderChart()}
           </div>
        )}
      </div>
    </div>
  );
}

export default App;
