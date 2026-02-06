import { P2PMessage, MessageType, ResourceSpec, TaskRequest, TaskResponse } from './protocol';
import { ConnectionManager } from './connection';
import { PeerDiscoveryService } from './discovery';

export interface RouterConfig {
  maxHops?: number;
  timeout?: number;
}

export class MessageRouter {
  private handlers: Map<MessageType, (message: P2PMessage) => Promise<any>> = new Map();

  constructor(
    private connectionManager: ConnectionManager,
    private discoveryService: PeerDiscoveryService,
    private config: RouterConfig = {}
  ) {}

  registerHandler(type: MessageType, handler: (message: P2PMessage) => Promise<any>): void {
    this.handlers.set(type, handler);
  }

  async route(message: P2PMessage): Promise<any> {
    const handler = this.handlers.get(message.type);
    if (handler) {
      return await handler(message);
    }

    // Default routing logic
    switch (message.type) {
      case MessageType.RESOURCE_QUERY:
        return this.handleResourceQuery(message);
      case MessageType.TASK_REQUEST:
        return this.handleTaskRequest(message);
      default:
        console.warn(`No handler for message type: ${message.type}`);
    }
  }

  private async handleResourceQuery(message: P2PMessage): Promise<any> {
    // Query DHT for resources
    const query = message.payload.query as Partial<ResourceSpec>;
    const key = `resource:${JSON.stringify(query)}`;
    
    const results = await this.discoveryService.queryDHT(key);
    return {
      type: MessageType.RESOURCE_RESPONSE,
      results: results.map((r) => JSON.parse(r)),
    };
  }

  private async handleTaskRequest(message: P2PMessage): Promise<TaskResponse> {
    const taskRequest: TaskRequest = message.payload;
    
    // Find suitable peer with required resources
    const peers = this.connectionManager.getConnectedPeers();
    const suitablePeer = peers.find((peer) => {
      return this.matchesResources(peer.resources, taskRequest.requirements);
    });

    if (!suitablePeer) {
      return {
        taskId: taskRequest.taskId,
        status: 'rejected',
        error: 'No suitable peer found',
      };
    }

    // Forward task request to suitable peer
    const forwardMessage: P2PMessage = {
      type: MessageType.TASK_REQUEST,
      from: message.from,
      to: suitablePeer.peerId,
      timestamp: Date.now(),
      payload: taskRequest,
    };

    const response = await this.connectionManager.sendMessage(suitablePeer.peerId, forwardMessage);
    
    return {
      taskId: taskRequest.taskId,
      status: response ? 'accepted' : 'rejected',
      workerId: suitablePeer.peerId,
    };
  }


  private matchesResources(available: ResourceSpec, required: Partial<ResourceSpec>): boolean {
    if (required.cpu && (!available.cpu || available.cpu.available < required.cpu.cores)) {
      return false;
    }
    if (required.gpu && (!available.gpu || available.gpu.available < required.gpu.count)) {
      return false;
    }
    if (required.memory && (!available.memory || available.memory.availableGB < required.memory.totalGB)) {
      return false;
    }
    if (required.storage && (!available.storage || available.storage.availableGB < required.storage.totalGB)) {
      return false;
    }
    return true;
  }

  async broadcastResourceAdvertisement(resources: ResourceSpec, peerId: string): Promise<void> {
    const message: P2PMessage = {
      type: MessageType.RESOURCE_ADVERTISE,
      from: peerId,
      timestamp: Date.now(),
      payload: { resources },
    };

    // Publish to DHT
    const key = `resource:${peerId}`;
    await this.discoveryService.publishToDHT(key, JSON.stringify(resources));

    // Broadcast to connected peers
    await this.connectionManager.broadcastMessage(message);
  }
}
