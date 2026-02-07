import React, { useState } from 'react';
import { submitJob } from '../services/api';

const LANGUAGE_OPTIONS = [
  { value: 'python', label: 'Python' },
  { value: 'bash', label: 'Bash (Ubuntu)' },
  { value: 'javascript', label: 'JS (Node)' },
] as const;

export default function Marketplace() {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState<string>('python');
  const [userId, setUserId] = useState('demo');
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setJobId(null);
    if (!code.trim()) {
      setError('Enter some code');
      return;
    }
    setLoading(true);
    try {
      const { job_id } = await submitJob({
        code: code.trim(),
        language,
        user_id: userId || 'demo',
      });
      setJobId(job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submit failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section style={{ padding: '1rem', maxWidth: 640 }}>
      <h2>Submit code</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '0.75rem' }}>
          <label htmlFor="language">Language</label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{ display: 'block', marginTop: 4, padding: 6, minWidth: 180 }}
          >
            {LANGUAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div style={{ marginBottom: '0.75rem' }}>
          <label htmlFor="code">Code</label>
          <textarea
            id="code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={
              language === 'python'
                ? 'print("Hello")'
                : language === 'bash'
                ? 'echo "Hello"'
                : 'console.log("Hello");'
            }
            rows={8}
            style={{ display: 'block', marginTop: 4, width: '100%', padding: 8, fontFamily: 'monospace' }}
          />
        </div>
        <div style={{ marginBottom: '0.75rem' }}>
          <label htmlFor="user_id">User ID (optional)</label>
          <input
            id="user_id"
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{ display: 'block', marginTop: 4, padding: 6, width: 200 }}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Submitting…' : 'Submit job'}
        </button>
      </form>
      {error && <p style={{ color: 'crimson', marginTop: 8 }}>{error}</p>}
      {jobId && (
        <p style={{ color: 'green', marginTop: 8 }}>
          Job submitted: <code>{jobId}</code>
        </p>
      )}
    </section>
  );
}
