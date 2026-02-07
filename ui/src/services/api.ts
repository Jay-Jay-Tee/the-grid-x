const DEFAULT_API_BASE = 'http://localhost:8081';

export interface SubmitJobParams {
  code: string;
  language: string;
  user_id?: string;
}

export async function submitJob(
  params: SubmitJobParams,
  apiBase: string = DEFAULT_API_BASE
): Promise<{ job_id: string }> {
  const res = await fetch(`${apiBase}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      code: params.code,
      language: params.language,
      user_id: params.user_id ?? 'demo',
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}
