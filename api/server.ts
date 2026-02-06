/**
 * Grid-X API Server
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { PeerDiscoveryService } from '../p2p/discovery';
import { ConnectionManager } from '../p2p/connection';
import { MessageRouter } from '../p2p/router';
import { GridXWebSocketServer } from './websocket';
import { generateToken } from './auth';

// Routes
import resourcesRouter from './routes/resources';
import tasksRouter from './routes/tasks';

const app = express();
const server = createServer(app);
const PORT = process.env.PORT || 3000;

// Initialize components
const wsServer = new GridXWebSocketServer(server);

// Simple user store (in production, use database)
const users: Map<string, { userId: string; username: string; email: string }> = new Map();

// Initialize P2P components
let discoveryService: PeerDiscoveryService;
let connectionManager: ConnectionManager;
let messageRouter: MessageRouter;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '10mb' })); // Limit request body size

// Rate limiting - stricter for auth endpoints
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 requests per window
  message: 'Too many authentication attempts, please try again later.',
});
app.use('/api/v1/auth/', authLimiter);

// General API rate limiting
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // 100 requests per window
  message: 'Too many requests, please try again later.',
});
app.use('/api/', apiLimiter);

// Task submission rate limiting (stricter)
const taskLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 10, // 10 tasks per minute
  message: 'Too many task submissions, please slow down.',
});
app.use('/api/v1/tasks', taskLimiter);

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    p2p: {
      connected: connectionManager?.getConnectedPeers().length || 0,
    },
    websocket: {
      clients: wsServer.getClientCount(),
    },
  });
});

// API Routes
app.use('/api/v1/resources', resourcesRouter);
app.use('/api/v1/tasks', taskLimiter, tasksRouter);

// Auth endpoint (simplified - in production, use proper registration)
app.post('/api/v1/auth/login', authLimiter, async (req, res) => {
  try {
    const { username, email } = req.body;

    if (!username || !email) {
      res.status(400).json({ error: 'Username and email are required' });
      return;
    }

    // Basic input validation
    if (username.length > 50 || email.length > 100) {
      res.status(400).json({ error: 'Invalid input length' });
      return;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      res.status(400).json({ error: 'Invalid email format' });
      return;
    }

    // Create or get user
    let user = Array.from(users.values()).find(
      (u) => u.username === username || u.email === email
    );

    if (!user) {
      const userId = require('uuid').v4();
      user = { userId, username, email };
      users.set(userId, user);
    }

    const token = generateToken({
      userId: user.userId,
      username: user.username,
      email: user.email,
    });

    res.json({
      success: true,
      token,
      user: {
        userId: user.userId,
        username: user.username,
        email: user.email,
      },
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Error handling middleware
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    error: process.env.NODE_ENV === 'production' ? 'Internal server error' : err.message,
  });
});

// 404 handler
app.use((req: express.Request, res: express.Response) => {
  res.status(404).json({ error: 'Not found' });
});

// Initialize P2P network
async function initializeP2P() {
  try {
    discoveryService = new PeerDiscoveryService({
      port: parseInt(process.env.P2P_PORT || '0'),
      enableMDNS: true,
      enableDHT: true,
      bootstrapNodes: process.env.BOOTSTRAP_NODES
        ? process.env.BOOTSTRAP_NODES.split(',')
        : [],
    });

    await discoveryService.start();

    connectionManager = new ConnectionManager({
      maxConnections: 50,
      heartbeatInterval: 30000,
    });

    connectionManager.setLibp2p(discoveryService['libp2p']!);

    messageRouter = new MessageRouter(
      connectionManager,
      discoveryService,
      { maxHops: 5, timeout: 30000 }
    );

    // Setup message handlers
    connectionManager.setOnMessage(async (message) => {
      await messageRouter.route(message);
    });

    console.log('P2P network initialized');
    console.log(`Peer ID: ${discoveryService.getPeerId()}`);
  } catch (error) {
    console.error('Failed to initialize P2P network:', error);
  }
}

// Start server
async function start() {
  try {
    await initializeP2P();

    server.listen(PORT, () => {
      console.log(`Grid-X API Server running on port ${PORT}`);
      console.log(`WebSocket server ready`);
      console.log(`P2P network: ${discoveryService ? 'Active' : 'Inactive'}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully...');
  if (discoveryService) {
    await discoveryService.stop();
  }
  if (connectionManager) {
    connectionManager.stop();
  }
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

// Export for testing
export { app, server, wsServer };

// Start if not in test mode
if (require.main === module) {
  start();
}
