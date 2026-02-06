import { createLibp2p, Libp2p } from 'libp2p';
import { tcp } from '@libp2p/tcp';
import { websockets } from '@libp2p/websockets';
import { mplex } from '@libp2p/mplex';
import { noise } from '@libp2p/noise';
import { mdns } from '@libp2p/mdns';
import { kadDHT } from '@libp2p/kad-dht';
import { bootstrap } from '@libp2p/bootstrap';
import { PeerInfo, MessageType, P2PMessage } from './protocol';

export interface DiscoveryConfig {
  port?: number;
  bootstrapNodes?: string[];
  enableMDNS?: boolean;
  enableDHT?: boolean;
}

export class PeerDiscoveryService {
  private libp2p: Libp2p | null = null;
  private discoveredPeers: Map<string, PeerInfo> = new Map();
  private onPeerDiscovered?: (peer: PeerInfo) => void;

  constructor(private config: DiscoveryConfig = {}) {}

  async start(): Promise<void> {
    const modules = {
      transports: [tcp(), websockets()],
      streamMuxers: [mplex()],
      connectionEncryption: [noise()],
      peerDiscovery: [],
      dht: undefined as any,
    };

    const peerDiscovery: any[] = [];

    // Add mDNS for local discovery
    if (this.config.enableMDNS !== false) {
      peerDiscovery.push(mdns());
    }

    // Add DHT for global discovery
    if (this.config.enableDHT !== false) {
      modules.dht = kadDHT({
        clientMode: false,
      });

      // Add bootstrap nodes if provided
      if (this.config.bootstrapNodes && this.config.bootstrapNodes.length > 0) {
        peerDiscovery.push(
          bootstrap({
            list: this.config.bootstrapNodes,
          })
        );
      }
    }

    modules.peerDiscovery = peerDiscovery;

    this.libp2p = await createLibp2p({
      addresses: {
        listen: [
          `/ip4/0.0.0.0/tcp/${this.config.port || 0}`,
          '/ip4/0.0.0.0/tcp/0/ws',
        ],
      },
      ...modules,
    });

    // Handle peer discovery events
    this.libp2p.addEventListener('peer:discovery', (evt) => {
      const peerId = evt.detail.id.toString();
      const addresses = evt.detail.addresses || [];
      
      if (addresses.length > 0) {
        const peerInfo: PeerInfo = {
          peerId,
          address: addresses[0].toString().split('/')[2] || 'unknown',
          port: parseInt(addresses[0].toString().split('/')[4] || '0'),
          resources: {},
          lastSeen: Date.now(),
        };

        this.discoveredPeers.set(peerId, peerInfo);
        this.onPeerDiscovered?.(peerInfo);
      }
    });

    await this.libp2p.start();
    console.log(`P2P node started with peer ID: ${this.libp2p.peerId.toString()}`);
  }

  async stop(): Promise<void> {
    if (this.libp2p) {
      await this.libp2p.stop();
      this.libp2p = null;
    }
  }

  getPeerId(): string | null {
    return this.libp2p?.peerId.toString() || null;
  }

  getDiscoveredPeers(): PeerInfo[] {
    return Array.from(this.discoveredPeers.values());
  }

  setOnPeerDiscovered(callback: (peer: PeerInfo) => void): void {
    this.onPeerDiscovered = callback;
  }

  async queryDHT(key: string): Promise<string[]> {
    if (!this.libp2p?.dht) {
      return [];
    }

    try {
      const values = [];
      for await (const value of this.libp2p.dht.get(key)) {
        values.push(value.toString());
      }
      return values;
    } catch (error) {
      console.error('DHT query error:', error);
      return [];
    }
  }

  async publishToDHT(key: string, value: string): Promise<void> {
    if (!this.libp2p?.dht) {
      return;
    }

    try {
      await this.libp2p.dht.put(key, new TextEncoder().encode(value));
    } catch (error) {
      console.error('DHT publish error:', error);
    }
  }
}
