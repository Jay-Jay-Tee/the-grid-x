/**
 * Grid-X Client SDK
 */

import WebSocket from 'ws';
import { GridXConfig, ResourceSpec, Task, UserAccount } from './types';

export class GridXClient {
  private apiEndpoint: string;
  private token?: string;
  private ws?: WebSocket;
  private wsReconnectInterval?: NodeJS.Timeout;
  private eventHandlers: Map<string, Set<(data: any) => void>> = new Map();

  constructor(config: GridXConfig) {
    this.apiEndpoint = config.apiEndpoint.replace(/\/$/, '');
    this.token = config.token;

    if (config.p2pEnabled !== false) {
      this.connectWebSocket();
    }
  }

  /**
   * Connect to WebSocket server
   */
  private connectWebSocket(): void {
    const wsUrl = this.apiEndpoint.replace(/^http/, 'ws') + '/ws';
    const url = this.token ? `${wsUrl}?token=${this.token}` : wsUrl;

    this.ws = new WebSocket(url);

    this.ws.on('open', () => {
      console.log('WebSocket connected');
      this.emit('connected', {});
    });

    this.ws.on('message', (data: Buffer) => {
      try {
        const message = JSON.parse(data.toString());
        this.handleWebSocketMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    });

    this.ws.on('error', (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', { error });
    });

    this.ws.on('close', () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected', {});
      // Attempt to reconnect
      this.scheduleReconnect();
    });
  }

  private scheduleReconnect(): void {
    if (this.wsReconnectInterval) return;

    this.wsReconnectInterval = setTimeout(() => {
      this.wsReconnectInterval = undefined;
      this.connectWebSocket();
    }, 5000);
  }

  private handleWebSocketMessage(message: any): void {
    const { type, payload } = message;
    this.emit(type, payload);
  }

  /**
   * Make authenticated API request
   */
  private async request(
    method: string,
    path: string,
    body?: any
  ): Promise<any> {
    const url = `${this.apiEndpoint}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const options: RequestInit = {
      method,
      headers,
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }

    return data;
  }

  /**
   * Authenticate and get token
   */
  async login(username: string, email: string): Promise<UserAccount> {
    const response = await this.request('POST', '/api/v1/auth/login', {
      username,
      email,
    });

    this.token = response.token;
    
    // Reconnect WebSocket with new token
    if (this.ws) {
      this.ws.close();
      this.connectWebSocket();
    }

    return response.user;
  }

  /**
   * Submit a task
   */
  async submitTask(task: Partial<Task>): Promise<Task> {
    const response = await this.request('POST', '/api/v1/tasks', {
      code: task.code,
      language: task.language || 'python',
      requirements: task.requirements || {},
      timeout: task.timeout || 300,
    });

    return response.task;
  }

  /**
   * Get task status
   */
  async getTask(taskId: string): Promise<Task> {
    const response = await this.request('GET', `/api/v1/tasks/${taskId}`);
    return response.task;
  }

  /**
   * Get user's tasks
   */
  async getTasks(): Promise<Task[]> {
    const response = await this.request('GET', '/api/v1/tasks');
    return response.tasks;
  }

  /**
   * Cancel a task
   */
  async cancelTask(taskId: string): Promise<void> {
    await this.request('DELETE', `/api/v1/tasks/${taskId}`);
  }

  /**
   * Query available resources
   */
  async queryResources(query?: Partial<ResourceSpec>): Promise<any[]> {
    const queryString = query
      ? '?' + new URLSearchParams(query as any).toString()
      : '';
    const response = await this.request('GET', `/api/v1/resources/query${queryString}`);
    return response.results;
  }


  /**
   * Subscribe to events
   */
  on(event: string, handler: (data: any) => void): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    // Send subscription message to server
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'subscribe',
          payload: { channels: [event] },
          timestamp: Date.now(),
        })
      );
    }
  }

  /**
   * Unsubscribe from events
   */
  off(event: string, handler: (data: any) => void): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Emit event to handlers
   */
  private emit(event: string, data: any): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Close connection
   */
  close(): void {
    if (this.wsReconnectInterval) {
      clearTimeout(this.wsReconnectInterval);
    }
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Export default instance creator
export function createClient(config: GridXConfig): GridXClient {
  return new GridXClient(config);
}
