/**
 * Grid-X SDK Types
 */

export interface GridXConfig {
  apiEndpoint: string;
  token?: string;
  p2pEnabled?: boolean;
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

export interface Task {
  taskId: string;
  code: string;
  language: string;
  requirements: Partial<ResourceSpec>;
  timeout?: number;
  status?: string;
  result?: any;
  error?: string;
}

export interface UserAccount {
  userId: string;
  username: string;
  email: string;
}
