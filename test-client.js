/**
 * Simple JavaScript test client (no TypeScript compilation needed)
 * Run with: node test-client.js
 * Requires Node.js 18+ for native fetch support
 */

const API_URL = 'http://localhost:3000';

async function test() {
  try {
    console.log('1. Testing health check...');
    const health = await fetch(`${API_URL}/health`);
    const healthData = await health.json();
    console.log('✓ Health:', healthData);

    console.log('\n2. Logging in...');
    const loginRes = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: 'testuser',
        email: 'test@example.com',
      }),
    });
    const loginData = await loginRes.json();
    console.log('✓ Login:', loginData);
    const token = loginData.token;

    console.log('\n3. Querying resources...');
    const resourcesRes = await fetch(`${API_URL}/api/v1/resources`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const resourcesData = await resourcesRes.json();
    console.log('✓ Resources:', resourcesData);

    console.log('\n4. Submitting a task...');
    const taskRes = await fetch(`${API_URL}/api/v1/tasks`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code: 'print("Hello from Grid-X!")',
        language: 'python',
        requirements: {
          cpu: { cores: 1 },
          memory: { totalGB: 1 },
        },
        timeout: 60,
      }),
    });
    const taskData = await taskRes.json();
    console.log('✓ Task submitted:', taskData);

    if (taskData.task && taskData.task.taskId) {
      console.log('\n5. Checking task status...');
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const statusRes = await fetch(
        `${API_URL}/api/v1/tasks/${taskData.task.taskId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      const statusData = await statusRes.json();
      console.log('✓ Task status:', statusData);
    }

    console.log('\n✅ All tests completed!');
  } catch (error) {
    console.error('❌ Error:', error.message);
    if (error.stack) {
      console.error(error.stack);
    }
  }
}

// Run test
test();
