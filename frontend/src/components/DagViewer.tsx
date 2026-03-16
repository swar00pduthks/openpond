import React, { useCallback } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface DagViewerProps {
  dag: any;
}

export const DagViewer: React.FC<DagViewerProps> = ({ dag }) => {
  // Convert AAF JSON DAG to ReactFlow format
  const initialNodes: any[] = [];
  const initialEdges: any[] = [];


  // Render Datasets as Input Nodes
  const allInputs = new Set<string>();
  dag.tasks.forEach((t: any) => t.inputs.forEach((i: string) => allInputs.add(i)));

  // Create nodes for raw datasets
  Array.from(allInputs).forEach((input, index) => {
    // Only create a raw dataset node if it's not the output of another task in this DAG
    const isGeneratedByTask = dag.tasks.some((t: any) => t.outputs.includes(input));
    if (!isGeneratedByTask) {
        initialNodes.push({
          id: input,
          position: { x: 50 + (index * 200), y: 50 },
          data: { label: input },
          style: { background: '#f0fdf4', border: '1px solid #16a34a', color: '#166534', borderRadius: '4px', padding: '10px' },
        });
    }
  });

  // Render Tasks as Processing Nodes
  dag.tasks.forEach((task: any, index: number) => {
    const xPos = 150 + (index * 50); // Staggering slightly
    const yPos = 200 + (index * 150);

    initialNodes.push({
      id: task.task_id,
      position: { x: xPos, y: yPos },
      data: { label: task.task_id },
      style: { background: '#f8fafc', border: '2px solid #3b82f6', color: '#1e40af', borderRadius: '8px', padding: '15px', width: '250px' },
    });

    // Edges from Inputs to this Task
    task.inputs.forEach((input: string) => {
      // Find where this input came from (a dataset node, or a previous task node)
      const sourceTask = dag.tasks.find((t: any) => t.outputs.includes(input));
      const sourceId = sourceTask ? sourceTask.task_id : input;

      initialEdges.push({
        id: `e-${sourceId}-${task.task_id}`,
        source: sourceId,
        target: task.task_id,
        animated: true,
        style: { stroke: '#94a3b8', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
      });
    });
  });

  const [nodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback((params: any) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  return (
    <div style={{ height: '400px', width: '100%', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        attributionPosition="bottom-right"
      >
        <Controls />
        <MiniMap nodeStrokeColor="#3b82f6" nodeColor="#f1f5f9" nodeBorderRadius={8} />
        <Background gap={16} size={1} />
      </ReactFlow>
    </div>
  );
};
