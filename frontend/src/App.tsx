import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import { Database, Upload, Play, Server, LineChart, FileJson, Sparkles, CheckCircle, Clock } from 'lucide-react';
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
  const [activeTab, setActiveTab] = useState<'notebook' | 'chart' | 'agent'>('agent');

  // AAF Agent State
  const [agentPrompt, setAgentPrompt] = useState("Clean the users table and join it with sales");
  const [agentDag, setAgentDag] = useState<any>(null);
  const [dagStatus, setDagStatus] = useState<'idle' | 'planned' | 'executing' | 'completed'>('idle');

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

  const handleAgentPlan = async () => {
    setLoading(true);
    setError(null);
    setAgentDag(null);
    setResults(null);
    setDagStatus('executing');

    try {
      const res = await axios.post('/api/v1/orchestrate/plan', {
        prompt: agentPrompt
      });
      setAgentDag(res.data);
      setDagStatus('planned');
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
      setDagStatus('idle');
    } finally {
      setLoading(false);
    }
  };

  const handleAgentExecute = async () => {
    setLoading(true);
    setError(null);
    setDagStatus('executing');

    try {
      const res = await axios.post('/api/v1/orchestrate/execute', {
        dag: agentDag
      });
      // Grab the results of the final task in the DAG
      const finalTask = res.data.results[res.data.results.length - 1];
      setResults(finalTask);
      setDagStatus('completed');
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
      setDagStatus('planned'); // Revert to planned so they can try again
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
           <button
             onClick={() => setActiveTab('agent')}
             className={`flex items-center space-x-2 px-3 py-2 rounded transition ${activeTab === 'agent' ? 'bg-purple-50 text-purple-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}>
             <Sparkles className="w-4 h-4 text-purple-500" />
             <span>AAF Agent</span>
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

            {error && (
              <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded shadow-sm">
                <strong>Error: </strong> {error}
              </div>
            )}

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

        {/* Agent Area */}
        {activeTab === 'agent' && (
           <div className="flex-1 flex flex-col p-6 space-y-4 overflow-y-auto">
            <div className="flex justify-between items-center">
               <div>
                 <h2 className="text-lg font-semibold text-gray-800 flex items-center">
                    <Sparkles className="w-5 h-5 text-purple-600 mr-2" /> AAF Orchestrator
                 </h2>
                 <p className="text-sm text-gray-500">Describe the data pipeline you want to run. No Airflow DAGs required.</p>
               </div>
            </div>

            <div className="flex space-x-2">
               <input
                 type="text"
                 value={agentPrompt}
                 onChange={e => setAgentPrompt(e.target.value)}
                 className="flex-1 border border-gray-300 rounded px-4 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
                 placeholder="e.g., Clean the users table and join it with sales..."
                 disabled={dagStatus === 'executing'}
               />
               <button
                 onClick={handleAgentPlan}
                 disabled={loading || dagStatus === 'executing'}
                 className="flex items-center px-6 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 transition shadow-sm font-medium">
                 {loading && dagStatus !== 'planned' ? "Agent Thinking..." : "Synthesize DAG"}
               </button>
            </div>

            {error && (
              <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded shadow-sm">
                <strong>Error: </strong> {error}
              </div>
            )}

            {agentDag && (
               <div className="mt-4 flex flex-col space-y-4">
                 <div className="p-4 bg-purple-50 border border-purple-100 rounded">
                   <h3 className="text-sm font-bold text-purple-800 mb-1">Agent Reasoning</h3>
                   <p className="text-sm text-purple-700 italic">"{agentDag.agent_reasoning}"</p>
                 </div>

                 <div className="border border-gray-200 rounded-md overflow-hidden shadow-sm bg-white">
                    <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 font-semibold text-gray-700 flex justify-between">
                       <span>Planned DAG: {agentDag.dag_id}</span>
                       <span className="text-xs bg-gray-200 px-2 py-1 rounded text-gray-600">{agentDag.tasks.length} Nodes</span>
                    </div>
                    <table className="min-w-full divide-y divide-gray-200 text-sm text-left">
                       <thead className="bg-gray-50">
                         <tr>
                            <th className="px-4 py-2 font-semibold text-gray-700">Task ID</th>
                            <th className="px-4 py-2 font-semibold text-gray-700">Inputs</th>
                            <th className="px-4 py-2 font-semibold text-gray-700">DuckDB SQL</th>
                         </tr>
                       </thead>
                       <tbody className="divide-y divide-gray-100">
                          {agentDag.tasks.map((task: any, i: number) => (
                             <tr key={i}>
                               <td className="px-4 py-3 text-gray-800 font-medium">{task.task_id}</td>
                               <td className="px-4 py-3 text-gray-600"><span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">{task.inputs.join(", ")}</span></td>
                               <td className="px-4 py-3 font-mono text-xs text-gray-600 break-words max-w-md">{task.query}</td>
                             </tr>
                          ))}
                       </tbody>
                    </table>
                 </div>

                 {dagStatus === 'planned' && (
                    <div className="flex space-x-4 mt-4">
                       <button onClick={handleAgentExecute} className="flex items-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition shadow-sm font-medium">
                          <CheckCircle className="w-4 h-4 mr-2" /> Approve & Execute
                       </button>
                       <button onClick={() => alert("Mock: DAG Scheduled for 8:00 AM daily via AAF.")} className="flex items-center px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition shadow-sm font-medium">
                          <Clock className="w-4 h-4 mr-2" /> Schedule
                       </button>
                    </div>
                 )}
               </div>
            )}

            {results && dagStatus === 'completed' && !error && (
              <div className="mt-6 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                   <h3 className="font-semibold text-gray-700">Final Task Results</h3>
                   <span className="text-xs text-gray-500">{results.row_count} rows fetched from DuckDB</span>
                </div>
                {renderTable()}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
