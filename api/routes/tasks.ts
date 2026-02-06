/**
 * Tasks API Routes
 */

import { Router, Request, Response } from 'express';
import { authenticateToken, AuthRequest } from '../auth';
import { TaskValidator } from '../task_validator';
import { v4 as uuidv4 } from 'uuid';
import { ResourceSpec } from '../../p2p/protocol';

const router = Router();
const taskValidator = new TaskValidator();

// In-memory task store (in production, use database)
const tasks: Map<string, any> = new Map();

/**
 * Submit a task
 * POST /api/v1/tasks
 */
router.post('/', authenticateToken, async (req: AuthRequest, res: Response) => {
  try {
    const { code, language, requirements, timeout } = req.body;

    if (!code || !language) {
      res.status(400).json({ error: 'Code and language are required' });
      return;
    }

    // Validate task
    const validation = taskValidator.validate({
      code,
      language,
      timeout,
      requirements,
    });

    if (!validation.valid) {
      res.status(400).json({
        error: 'Task validation failed',
        errors: validation.errors,
        warnings: validation.warnings,
      });
      return;
    }

    // Log warnings if any
    if (validation.warnings.length > 0) {
      console.warn('Task validation warnings:', validation.warnings);
    }

    const taskId = uuidv4();
    const task = {
      taskId,
      userId: req.user!.userId,
      code,
      language,
      requirements: requirements || {},
      timeout: timeout || 300,
      status: 'pending',
      createdAt: new Date(),
    };

    tasks.set(taskId, task);

    // TODO: Match with worker via P2P network

    res.status(201).json({
      success: true,
      task,
      warnings: validation.warnings,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Get task status
 * GET /api/v1/tasks/:taskId
 */
router.get('/:taskId', authenticateToken, (req: AuthRequest, res: Response) => {
  try {
    const { taskId } = req.params;
    const task = tasks.get(taskId);

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    // Check authorization
    if (task.userId !== req.user!.userId) {
      res.status(403).json({ error: 'Unauthorized' });
      return;
    }

    res.json({
      success: true,
      task,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Get user's tasks
 * GET /api/v1/tasks
 */
router.get('/', authenticateToken, (req: AuthRequest, res: Response) => {
  try {
    const userId = req.user!.userId;
    const userTasks = Array.from(tasks.values())
      .filter((task) => task.userId === userId)
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());

    res.json({
      success: true,
      tasks: userTasks,
      count: userTasks.length,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * Cancel a task
 * DELETE /api/v1/tasks/:taskId
 */
router.delete('/:taskId', authenticateToken, (req: AuthRequest, res: Response) => {
  try {
    const { taskId } = req.params;
    const task = tasks.get(taskId);

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    // Check authorization
    if (task.userId !== req.user!.userId) {
      res.status(403).json({ error: 'Unauthorized' });
      return;
    }

    // Only allow cancellation of pending/queued tasks
    if (['completed', 'failed'].includes(task.status)) {
      res.status(400).json({ error: 'Cannot cancel completed or failed task' });
      return;
    }

    task.status = 'cancelled';
    task.cancelledAt = new Date();

    res.json({
      success: true,
      message: 'Task cancelled',
      task,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
