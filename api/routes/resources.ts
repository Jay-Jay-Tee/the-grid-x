/**
 * Resources API Routes
 */

import { Router, Request, Response } from 'express';
import { authenticateToken, AuthRequest } from '../auth';
import { PeerDiscoveryService } from '../../p2p/discovery';
import { MessageRouter } from '../../p2p/router';
import { ResourceSpec } from '../../p2p/protocol';

const router = Router();

// Store advertised resources (in production, this would be in a database)
const advertisedResources: Map<string, { peerId: string; resources: ResourceSpec; timestamp: number }> = new Map();

/**
 * Advertise available resources
 * POST /api/v1/resources/advertise
 */
router.post('/advertise', authenticateToken, (req: AuthRequest, res: Response) => {
  try {
    const resources = req.body as ResourceSpec;
    const peerId = req.user?.userId || 'unknown';

    advertisedResources.set(peerId, {
      peerId,
      resources,
      timestamp: Date.now(),
    });

    res.json({
      success: true,
      message: 'Resources advertised successfully',
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Query available resources
 * GET /api/v1/resources/query
 */
router.get('/query', (req: Request, res: Response) => {
  try {
    const query = req.query as Partial<ResourceSpec>;
    
    // Filter resources based on query
    const results = Array.from(advertisedResources.values())
      .filter((entry) => {
        // Simple matching logic
        if (query.cpu && (!entry.resources.cpu || entry.resources.cpu.available < query.cpu.cores)) {
          return false;
        }
        if (query.gpu && (!entry.resources.gpu || entry.resources.gpu.available < query.gpu.count)) {
          return false;
        }
        if (query.memory && (!entry.resources.memory || entry.resources.memory.availableGB < query.memory.totalGB)) {
          return false;
        }
        return true;
      })
      .map((entry) => ({
        peerId: entry.peerId,
        resources: entry.resources,
        lastSeen: entry.timestamp,
      }));

    res.json({
      success: true,
      results,
      count: results.length,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Get all advertised resources
 * GET /api/v1/resources
 */
router.get('/', (req: Request, res: Response) => {
  try {
    const results = Array.from(advertisedResources.values()).map((entry) => ({
      peerId: entry.peerId,
      resources: entry.resources,
      lastSeen: entry.timestamp,
    }));

    res.json({
      success: true,
      results,
      count: results.length,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Get resource by peer ID
 * GET /api/v1/resources/:peerId
 */
router.get('/:peerId', (req: Request, res: Response) => {
  try {
    const { peerId } = req.params;
    const entry = advertisedResources.get(peerId);

    if (!entry) {
      res.status(404).json({ error: 'Resource not found' });
      return;
    }

    res.json({
      success: true,
      peerId: entry.peerId,
      resources: entry.resources,
      lastSeen: entry.timestamp,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
