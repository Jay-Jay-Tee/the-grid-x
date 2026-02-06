/**
 * Grid-X P2P Protocol Definitions
 */

export enum MessageType {
  RESOURCE_ADVERTISE = 'RESOURCE_ADVERTISE',
  RESOURCE_QUERY = 'RESOURCE_QUERY',
  RESOURCE_RESPONSE = 'RESOURCE_RESPONSE',
  TASK_REQUEST = 'TASK_REQUEST',
  TASK_RESPONSE = 'TASK_RESPONSE',
  HEARTBEAT = 'HEARTBEAT',
}

export interface ResourceSpec {
  cpu?: {
    cores: number;
    available: number;
  };
  gpu?: {
    count: number;
    available: number;
    model?: string;
    memoryGB?: number;
  };
  memory?: {
    totalGB: number;
    availableGB: number;
  };
  storage?: {
    totalGB: number;
    availableGB: number;
  };
  bandwidth?: {
    uploadMbps: number;
    downloadMbps: number;
  };
}

export interface PeerInfo {
  peerId: string;
  address: string;
  port: number;
  resources: ResourceSpec;
  reputation?: number;
  lastSeen: number;
}

export interface P2PMessage {
  type: MessageType;
  from: string;
  to?: string;
  timestamp: number;
  payload: any;
  signature?: string;
}

export interface TaskRequest {
  taskId: string;
  code: string;
  language: string;
  requirements: ResourceSpec;
  timeout: number;
}

export interface TaskResponse {
  taskId: string;
  status: 'accepted' | 'rejected' | 'completed';
  result?: any;
  error?: string;
  workerId?: string;
}

