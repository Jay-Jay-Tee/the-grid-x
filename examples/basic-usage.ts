/**
 * Basic Grid-X Client Usage Example
 */

import { GridXClient } from '../sdk/client';

async function main() {
  // Create client
  const client = new GridXClient({
    apiEndpoint: 'http://localhost:3000',
    p2pEnabled: true,
  });

  try {
    // Login
    console.log('Logging in...');
    const user = await client.login('testuser', 'test@example.com');
    console.log('Logged in:', user);

    // Set token for subsequent requests
    client['token'] = user.userId; // In real implementation, token would be returned

    // Query available resources
    console.log('\nQuerying resources...');
    const resources = await client.queryResources({
      cpu: { cores: 2 },
      memory: { totalGB: 4 },
    });
    console.log('Available resources:', resources);

    // Submit a task
    console.log('\nSubmitting task...');
    const task = await client.submitTask({
      code: 'print("Hello from Grid-X!")',
      language: 'python',
      requirements: {
        cpu: { cores: 1 },
        memory: { totalGB: 1 },
      },
      timeout: 60,
    });
    console.log('Task submitted:', task);

    // Listen for task updates
    client.on('task_update', (data) => {
      console.log('Task update:', data);
      if (data.status === 'completed') {
        console.log('Task completed!', data.result);
      }
    });

    // Wait for task completion
    let taskStatus = task.status;
    while (taskStatus === 'pending' || taskStatus === 'running') {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const updatedTask = await client.getTask(task.taskId);
      taskStatus = updatedTask.status;
      console.log('Task status:', taskStatus);
    }

    // Get final task result
    const finalTask = await client.getTask(task.taskId);
    console.log('\nFinal task result:', finalTask);

  } catch (error) {
    console.error('Error:', error);
  } finally {
    client.close();
  }
}

// Run example
if (require.main === module) {
  main().catch(console.error);
}
