import { Libp2p } from 'libp2p';
import { PeerInfo, P2PMessage, MessageType } from './protocol';

export interface ConnectionConfig {
  maxConnections?: number;
  heartbeatInterval?: number;
  connectionTimeout?: number;
}

export class ConnectionManager {
  private libp2p: Libp2p | null = null;
  private connections: Map<string, { peer: PeerInfo; lastHeartbeat: number }> = new Map();
  private heartbeatInterval?: NodeJS.Timeout;
  private onMessage?: (message: P2PMessage) => void;

  constructor(private config: ConnectionConfig = {}) {}

  setLibp2p(libp2p: Libp2p): void {
    this.libp2p = libp2p;
    this.setupEventHandlers();
    this.startHeartbeat();
  }

  private setupEventHandlers(): void {
    if (!this.libp2p) return;

    this.libp2p.addEventListener('peer:connect', (evt) => {
      const peerId = evt.detail.toString();
      console.log(`Connected to peer: ${peerId}`);
    });

    this.libp2p.addEventListener('peer:disconnect', (evt) => {
      const peerId = evt.detail.toString();
      console.log(`Disconnected from peer: ${peerId}`);
      this.connections.delete(peerId);
    });
  }

  async connectToPeer(peerInfo: PeerInfo): Promise<boolean> {
    if (!this.libp2p) {
      throw new Error('Libp2p not initialized');
    }

    const maxConnections = this.config.maxConnections || 50;
    if (this.connections.size >= maxConnections) {
      console.warn('Max connections reached');
      return false;
    }

    try {
      const multiaddr = `/ip4/${peerInfo.address}/tcp/${peerInfo.port}`;
      await this.libp2p.dial(multiaddr);
      
      this.connections.set(peerInfo.peerId, {
        peer: peerInfo,
        lastHeartbeat: Date.now(),
      });

      return true;
    } catch (error) {
      console.error(`Failed to connect to peer ${peerInfo.peerId}:`, error);
      return false;
    }
  }

  async sendMessage(peerId: string, message: P2PMessage): Promise<boolean> {
    if (!this.libp2p) {
      throw new Error('Libp2p not initialized');
    }

    try {
      const stream = await this.libp2p.dialProtocol(peerId, '/grid-x/1.0.0');
      const encoder = new TextEncoder();
      const decoder = new TextDecoder();
      
      await stream.write(encoder.encode(JSON.stringify(message)));
      
      // Read response if needed
      const response = await stream.read();
      if (response) {
        const responseMessage = JSON.parse(decoder.decode(response.subarray()));
        return responseMessage.status === 'ok';
      }

      return true;
    } catch (error) {
      console.error(`Failed to send message to ${peerId}:`, error);
      return false;
    }
  }

  async broadcastMessage(message: P2PMessage): Promise<number> {
    let successCount = 0;
    const promises = Array.from(this.connections.keys()).map(async (peerId) => {
      const success = await this.sendMessage(peerId, message);
      if (success) successCount++;
    });

    await Promise.all(promises);
    return successCount;
  }

  getConnectedPeers(): PeerInfo[] {
    return Array.from(this.connections.values()).map((conn) => conn.peer);
  }

  isConnected(peerId: string): boolean {
    return this.connections.has(peerId);
  }

  setOnMessage(callback: (message: P2PMessage) => void): void {
    this.onMessage = callback;
    this.setupMessageHandler();
  }

  private setupMessageHandler(): void {
    if (!this.libp2p || !this.onMessage) return;

    // Handle incoming streams
    this.libp2p.handle('/grid-x/1.0.0', async ({ stream }) => {
      const decoder = new TextDecoder();
      const encoder = new TextEncoder();

      try {
        const data = await stream.read();
        if (data) {
          const message: P2PMessage = JSON.parse(decoder.decode(data.subarray()));
          this.onMessage?.(message);

          // Send acknowledgment
          await stream.write(encoder.encode(JSON.stringify({ status: 'ok' })));
        }
      } catch (error) {
        console.error('Error handling message:', error);
        await stream.write(encoder.encode(JSON.stringify({ status: 'error', error: String(error) })));
      }
    });
  }

  private startHeartbeat(): void {
    const interval = this.config.heartbeatInterval || 30000; // 30 seconds

    this.heartbeatInterval = setInterval(() => {
      this.sendHeartbeats();
    }, interval);
  }

  private async sendHeartbeats(): Promise<void> {
    const timeout = this.config.connectionTimeout || 60000; // 60 seconds
    const now = Date.now();

    const deadPeers: string[] = [];
    for (const [peerId, conn] of this.connections.entries()) {
      if (now - conn.lastHeartbeat > timeout) {
        deadPeers.push(peerId);
      } else {
        // Send heartbeat
        const message: P2PMessage = {
          type: MessageType.HEARTBEAT,
          from: this.libp2p?.peerId.toString() || '',
          timestamp: now,
          payload: {},
        };

        await this.sendMessage(peerId, message);
        conn.lastHeartbeat = now;
      }
    }

    // Remove dead peers
    deadPeers.forEach((peerId) => this.connections.delete(peerId));
  }

  stop(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
  }
}
