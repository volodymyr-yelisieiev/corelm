export type WorkflowNodeContract = {
  id: string;
  type: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
};

export type WorkflowEdgeContract = {
  id: string;
  source: string;
  target: string;
};

export type WorkflowContract = {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNodeContract[];
  edges: WorkflowEdgeContract[];
};
