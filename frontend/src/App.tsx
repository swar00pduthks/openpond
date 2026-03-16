import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import { Database, Upload, Play, LineChart, FileJson, Sparkles, CheckCircle, Clock, Send, Bot, User, Menu, ChevronLeft } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { OpenPondLogo } from './components/Logo';
import { DagViewer } from './components/DagViewer';

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
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // AAF Agent Chat State
  const [chatInput, setChatInput] = useState("Clean the users table and join it with sales");
  const [chatHistory, setChatHistory] = useState<{role: 'user'|'agent', text: string, dag?: any}[]>([]);
  const [dagStatus, setDagStatus] = useState<'idle' | 'planned' | 'executing' | 'completed'>('idle');
  const [activeDag, setActiveDag] = useState<any>(null);

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
      const res = await axios.post('/api/v1/query/execute', { query, datasets_used: usedDatasets });
      setResults(res.data.result);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAgentPlan = async () => {
    if (!chatInput.trim()) return;
    const currentInput = chatInput;

    // Add User Message
    setChatHistory(prev => [...prev, { role: 'user', text: currentInput }]);
    setChatInput("");

    setLoading(true);
    setError(null);
    setActiveDag(null);
    setResults(null);
    setDagStatus('executing');

    try {
      const res = await axios.post('/api/v1/orchestrate/plan', { prompt: currentInput });
      setActiveDag(res.data);
      setDagStatus('planned');
      // Add Agent Response
      setChatHistory(prev => [...prev, {
        role: 'agent',
        text: res.data.agent_reasoning,
        dag: res.data
      }]);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
      setDagStatus('idle');
      setChatHistory(prev => [...prev, { role: 'agent', text: "Sorry, I encountered an error synthesizing the DAG."}]);
    } finally {
      setLoading(false);
    }
  };

  const handleAgentExecute = async (dag: any) => {
    setLoading(true);
    setError(null);
    setDagStatus('executing');

    try {
      const res = await axios.post('/api/v1/orchestrate/execute', { dag });
      const finalTask = res.data.results[res.data.results.length - 1];
      setResults(finalTask);
      setDagStatus('completed');
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
      setDagStatus('planned');
    } finally {
      setLoading(false);
    }
  };

  const renderTable = () => {
    if (!results || !results.data || results.data.length === 0) return <div>No data</div>;
    const cols = Object.keys(results.data[0]);

    return (
      <div className="overflow-x-auto border border-gray-200 rounded-md shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-sm text-left">
          <thead className="bg-gray-50">
            <tr>
              {cols.map((col, i) => (
                <th key={i} className="px-4 py-2 font-semibold text-gray-700 whitespace-nowrap">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {results.data.map((row: any, i: number) => (
              <tr key={i} className="hover:bg-blue-50/50 transition">
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
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey={xAxisCol} tick={{fill: '#64748b'}} axisLine={false} tickLine={false} />
            <YAxis tick={{fill: '#64748b'}} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}/>
            <Legend />
            <Bar dataKey={yAxisCol} fill="#0ea5e9" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-[#f8fafc] font-sans text-slate-800">

      {/* Sidebar - Collapsible OpenMetadata Style */}
      <div className={`bg-white border-r border-slate-200 flex flex-col shadow-sm z-10 transition-all duration-300 ${sidebarOpen ? 'w-64' : 'w-16'}`}>
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-3 overflow-hidden">
            <OpenPondLogo className="w-8 h-8 shrink-0" />
            {sidebarOpen && <h1 className="text-xl font-bold tracking-tight text-slate-800 whitespace-nowrap">OpenPond</h1>}
          </div>
          {sidebarOpen && (
            <button onClick={() => setSidebarOpen(false)} className="text-slate-400 hover:text-slate-600">
              <ChevronLeft className="w-5 h-5" />
            </button>
          )}
        </div>

        {!sidebarOpen && (
           <button onClick={() => setSidebarOpen(true)} className="p-4 mx-auto text-slate-400 hover:text-slate-600">
              <Menu className="w-5 h-5" />
           </button>
        )}

        <div className="flex-1 overflow-y-auto p-4 flex flex-col items-center">
          {sidebarOpen && <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 w-full">Data Catalog</h2>}
          <ul className="space-y-2 w-full">
            {datasets.map((d, i) => (
              <li key={i} className={`flex items-center text-sm p-2 hover:bg-sky-50 rounded text-slate-700 cursor-pointer transition ${!sidebarOpen ? 'justify-center' : ''}`} title={d.name}>
                <Database className="w-4 h-4 text-sky-500 shrink-0" />
                {sidebarOpen && <span className="ml-2 truncate">{d.name}</span>}
              </li>
            ))}
            {datasets.length === 0 && sidebarOpen && <p className="text-xs text-slate-400 italic w-full">No datasets registered.</p>}
          </ul>
        </div>

        <div className="p-4 border-t border-slate-200">
          <label className={`flex items-center justify-center w-full py-2 text-sm font-medium text-white bg-sky-600 rounded-md cursor-pointer hover:bg-sky-700 transition shadow-sm ${sidebarOpen ? 'px-4' : 'px-0'}`} title="Upload File">
            <Upload className="w-4 h-4" />
            {sidebarOpen && <span className="ml-2">{uploading ? "Uploading..." : "Upload File"}</span>}
            <input type="file" className="hidden" accept=".csv,.parquet" onChange={handleUpload} disabled={uploading} />
          </label>
        </div>
      </div>

      {/* Main Content - Workspace */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Header Tabs */}
        <div className="bg-white border-b border-slate-200 px-6 py-3 flex space-x-4">
           <button
             onClick={() => setActiveTab('notebook')}
             className={`flex items-center space-x-2 px-3 py-2 rounded transition ${activeTab === 'notebook' ? 'bg-sky-50 text-sky-700 font-medium' : 'text-slate-600 hover:bg-slate-100'}`}>
             <FileJson className="w-4 h-4" />
             <span>Notebook</span>
           </button>
           <button
             onClick={() => setActiveTab('chart')}
             className={`flex items-center space-x-2 px-3 py-2 rounded transition ${activeTab === 'chart' ? 'bg-sky-50 text-sky-700 font-medium' : 'text-slate-600 hover:bg-slate-100'}`}>
             <LineChart className="w-4 h-4" />
             <span>Dashboard</span>
           </button>
           <button
             onClick={() => setActiveTab('agent')}
             className={`flex items-center space-x-2 px-3 py-2 rounded transition ${activeTab === 'agent' ? 'bg-purple-50 text-purple-700 font-medium' : 'text-slate-600 hover:bg-slate-100'}`}>
             <Sparkles className="w-4 h-4 text-purple-500" />
             <span>AAF Agent</span>
           </button>
        </div>

        {/* Notebook Area */}
        {activeTab === 'notebook' && (
          <div className="flex-1 flex flex-col p-6 space-y-4 overflow-y-auto">
            <div className="flex justify-between items-center">
               <h2 className="text-lg font-semibold text-slate-800">SQL Workspace</h2>
               <button
                 onClick={handleRunQuery}
                 disabled={loading}
                 className="flex items-center px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50 transition shadow-sm font-medium">
                 <Play className="w-4 h-4 mr-2" />
                 {loading ? "Running..." : "Run via OpenPond"}
               </button>
            </div>

            <div className="border border-slate-300 rounded-md overflow-hidden shadow-sm h-64 bg-white">
              <Editor
                height="100%"
                defaultLanguage="sql"
                theme="vs-light"
                value={query}
                onChange={(val) => setQuery(val || "")}
                options={{ minimap: { enabled: false }, fontSize: 14, padding: { top: 16 } }}
              />
            </div>

            {error && (
              <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded-md shadow-sm">
                <strong>Error: </strong> {error}
              </div>
            )}

            {results && !error && (
              <div className="mt-6 flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex items-center justify-between mb-3">
                   <h3 className="font-semibold text-slate-700 text-lg">Results</h3>
                   <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-1 rounded-full font-medium">{results.row_count} rows from DuckDB</span>
                </div>
                {renderTable()}
              </div>
            )}
          </div>
        )}

        {/* Chart Area */}
        {activeTab === 'chart' && (
           <div className="flex-1 p-6 overflow-y-auto bg-slate-50">
              {renderChart()}
           </div>
        )}

        {/* Agent Area (Chat UI + DAG) */}
        {activeTab === 'agent' && (
           <div className="flex-1 flex flex-col overflow-hidden bg-slate-50 relative">

             {/* Chat History Area */}
             <div className="flex-1 overflow-y-auto p-6 space-y-6 pb-32">
                <div className="text-center py-8">
                  <div className="mx-auto bg-purple-100 w-16 h-16 rounded-full flex items-center justify-center mb-4 shadow-inner">
                     <Sparkles className="w-8 h-8 text-purple-600" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-800 mb-2">OpenPond AAF Orchestrator</h2>
                  <p className="text-slate-500 max-w-md mx-auto">Describe your data pipeline in natural language. The Agent will synthesize an execution DAG and track lineage automatically in Marquez.</p>
                </div>

                {chatHistory.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div className={`shrink-0 flex items-center justify-center w-8 h-8 rounded-full shadow-sm ${msg.role === 'user' ? 'bg-slate-200 ml-3' : 'bg-purple-100 mr-3'}`}>
                        {msg.role === 'user' ? <User className="w-5 h-5 text-slate-600" /> : <Bot className="w-5 h-5 text-purple-600" />}
                      </div>

                      <div className="flex flex-col space-y-3">
                        {/* Text Bubble */}
                        <div className={`p-4 rounded-2xl shadow-sm text-sm ${msg.role === 'user' ? 'bg-sky-600 text-white rounded-tr-sm' : 'bg-white border border-slate-200 text-slate-700 rounded-tl-sm'}`}>
                          {msg.text}
                        </div>

                        {/* DAG Visualization if Agent returned one */}
                        {msg.role === 'agent' && msg.dag && (
                           <div className="bg-white border border-purple-200 rounded-xl shadow-md overflow-hidden w-[600px] animate-in fade-in duration-700">
                             <div className="bg-purple-50 px-4 py-2 border-b border-purple-100 flex justify-between items-center">
                               <span className="text-xs font-bold text-purple-800 uppercase tracking-wide">Generated DAG Plan</span>
                               <span className="text-xs bg-purple-200 text-purple-800 px-2 py-0.5 rounded-full">{msg.dag.tasks.length} Nodes</span>
                             </div>

                             <div className="p-4">
                                <DagViewer dag={msg.dag} />
                             </div>

                             {/* Action Bar for the active DAG */}
                             {dagStatus === 'planned' && activeDag?.dag_id === msg.dag.dag_id && (
                                <div className="p-4 bg-slate-50 border-t border-slate-200 flex space-x-3">
                                   <button onClick={() => handleAgentExecute(msg.dag)} className="flex-1 flex justify-center items-center px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 transition shadow-sm font-medium">
                                      <CheckCircle className="w-4 h-4 mr-2" /> Approve & Execute
                                   </button>
                                   <button onClick={() => alert("Mock: DAG Scheduled via AAF.")} className="flex-1 flex justify-center items-center px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-md hover:bg-slate-50 transition shadow-sm font-medium">
                                      <Clock className="w-4 h-4 mr-2" /> Schedule Task
                                   </button>
                                </div>
                             )}
                           </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {error && (
                  <div className="flex justify-center">
                    <div className="bg-red-50 text-red-700 px-4 py-2 rounded-md border border-red-200 text-sm shadow-sm flex items-center">
                      <span className="font-semibold mr-2">Error:</span> {error}
                    </div>
                  </div>
                )}

                {/* Agent Execution Results appearing in stream */}
                {results && dagStatus === 'completed' && !error && (
                   <div className="flex justify-start">
                     <div className="flex max-w-[90%] flex-row">
                        <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-full bg-emerald-100 shadow-sm mr-3">
                          <CheckCircle className="w-5 h-5 text-emerald-600" />
                        </div>
                        <div className="flex flex-col space-y-2">
                          <div className="p-3 bg-white border border-emerald-200 text-emerald-800 rounded-2xl rounded-tl-sm shadow-sm text-sm font-medium">
                            DAG Executed Successfully. Lineage synced to Marquez.
                          </div>
                          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-2">
                            {renderTable()}
                          </div>
                        </div>
                     </div>
                   </div>
                )}

                {/* Loading Indicator */}
                {loading && (
                   <div className="flex justify-start">
                    <div className="flex flex-row">
                      <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-full bg-purple-100 shadow-sm mr-3">
                        <Bot className="w-5 h-5 text-purple-600 animate-pulse" />
                      </div>
                      <div className="p-4 bg-white border border-slate-200 text-slate-500 rounded-2xl rounded-tl-sm shadow-sm text-sm flex items-center space-x-2">
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></div>
                      </div>
                    </div>
                  </div>
                )}
             </div>

             {/* Sticky Chat Input Bar */}
             <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent pt-10">
                <div className="max-w-4xl mx-auto flex shadow-lg rounded-full overflow-hidden border border-slate-300 bg-white">
                   <input
                     type="text"
                     value={chatInput}
                     onChange={e => setChatInput(e.target.value)}
                     onKeyDown={e => e.key === 'Enter' && !loading && handleAgentPlan()}
                     className="flex-1 px-6 py-4 text-slate-700 focus:outline-none bg-transparent"
                     placeholder="Ask OpenPond Agent to orchestrate..."
                     disabled={loading || dagStatus === 'executing'}
                   />
                   <button
                     onClick={handleAgentPlan}
                     disabled={loading || dagStatus === 'executing' || !chatInput.trim()}
                     className="px-6 py-4 bg-purple-600 text-white hover:bg-purple-700 disabled:bg-slate-300 transition-colors flex items-center justify-center">
                     <Send className="w-5 h-5" />
                   </button>
                </div>
             </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
