/**
 * WebSocket Server - Real-time updates for tasks and resources
 */

import { WebSocketServer, WebSocket } from 'ws';
import { Server } from 'http';
import { verifyToken, UserPayload } from './auth';

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: number;
}

export class GridXWebSocketServer {
  private wss: WebSocketServer;
  private clients: Map<string, { ws: WebSocket; user?: UserPayload }> = new Map();

  constructor(server: Server) {
    this.wss = new WebSocketServer({ server });

    this.wss.on('connection', (ws: WebSocket, req) => {
      this.handleConnection(ws, req);
    });
  }

  private handleConnection(ws: WebSocket, req: any): void {
    const clientId = this.generateClientId();
    console.log(`WebSocket client connected: ${clientId}`);

    // Try to authenticate from query params or headers
    const token = this.extractToken(req);
    let user: UserPayload | undefined;

    if (token) {
      user = verifyToken(token);
      if (user) {
        console.log(`Authenticated user: ${user.username}`);
      }
    }

    this.clients.set(clientId, { ws, user });

    // Send welcome message
    this.sendToClient(clientId, {
      type: 'connected',
      payload: { clientId, authenticated: !!user },
      timestamp: Date.now(),
    });

    // Handle messages
    ws.on('message', (data: Buffer) => {
      try {
        const message: WebSocketMessage = JSON.parse(data.toString());
        this.handleMessage(clientId, message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        this.sendError(clientId, 'Invalid message format');
      }
    });

    // Handle disconnect
    ws.on('close', () => {
      console.log(`WebSocket client disconnected: ${clientId}`);
      this.clients.delete(clientId);
    });

    // Handle errors
    ws.on('error', (error) => {
      console.error(`WebSocket error for client ${clientId}:`, error);
      this.clients.delete(clientId);
    });
  }

  private extractToken(req: any): string | null {
    // Try query parameter
    if (req.url) {
      const url = new URL(req.url, `http://${req.headers.host}`);
      const token = url.searchParams.get('token');
      if (token) return token;
    }

    // Try authorization header
    const authHeader = req.headers['authorization'];
    if (authHeader) {
      const parts = authHeader.split(' ');
      if (parts.length === 2 && parts[0] === 'Bearer') {
        return parts[1];
      }
    }

    return null;
  }

  private handleMessage(clientId: string, message: WebSocketMessage): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    switch (message.type) {
      case 'subscribe':
        // Handle subscription requests
        this.handleSubscribe(clientId, message.payload);
        break;
      case 'unsubscribe':
        // Handle unsubscription requests
        this.handleUnsubscribe(clientId, message.payload);
        break;
      case 'ping':
        // Respond to ping
        this.sendToClient(clientId, {
          type: 'pong',
          payload: {},
          timestamp: Date.now(),
        });
        break;
      default:
        this.sendError(clientId, `Unknown message type: ${message.type}`);
    }
  }

  private handleSubscribe(clientId: string, payload: any): void {
    // In production, track subscriptions per client
    this.sendToClient(clientId, {
      type: 'subscribed',
      payload: { channels: payload.channels || [] },
      timestamp: Date.now(),
    });
  }

  private handleUnsubscribe(clientId: string, payload: any): void {
    this.sendToClient(clientId, {
      type: 'unsubscribed',
      payload: { channels: payload.channels || [] },
      timestamp: Date.now(),
    });
  }

  /**
   * Broadcast message to all clients
   */
  broadcast(message: WebSocketMessage): void {
    const data = JSON.stringify(message);
    this.clients.forEach((client) => {
      if (client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(data);
      }
    });
  }

  /**
   * Send message to specific client
   */
  sendToClient(clientId: string, message: WebSocketMessage): void {
    const client = this.clients.get(clientId);
    if (client && client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Send error to client
   */
  sendError(clientId: string, error: string): void {
    this.sendToClient(clientId, {
      type: 'error',
      payload: { error },
      timestamp: Date.now(),
    });
  }

  /**
   * Broadcast task update
   */
  broadcastTaskUpdate(taskId: string, status: string, data: any): void {
    this.broadcast({
      type: 'task_update',
      payload: { taskId, status, ...data },
      timestamp: Date.now(),
    });
  }

  /**
   * Broadcast resource update
   */
  broadcastResourceUpdate(peerId: string, resources: any): void {
    this.broadcast({
      type: 'resource_update',
      payload: { peerId, resources },
      timestamp: Date.now(),
    });
  }


  private generateClientId(): string {
    return `client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get connected clients count
   */
  getClientCount(): number {
    return this.clients.size;
  }
}
