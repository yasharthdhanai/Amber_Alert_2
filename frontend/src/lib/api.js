const API_URL = 'http://localhost:8000/api';

export async function fetchCases() {
  const res = await fetch(`${API_URL}/cases/`);
  if (!res.ok) throw new Error('Failed to fetch cases');
  return res.json();
}

export async function fetchCase(id) {
  const res = await fetch(`${API_URL}/cases/${id}`);
  if (!res.ok) throw new Error('Failed to fetch case');
  return res.json();
}

export function getCasePhotoUrl(id) {
  return `${API_URL}/cases/${id}/photo`;
}

export function getMatchScreenshotUrl(caseId, matchId) {
  return `${API_URL}/cases/${caseId}/matches/${matchId}/screenshot`;
}

export async function createCase(formData) {
  const res = await fetch(`${API_URL}/cases/`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to create case');
  }
  return res.json();
}

export async function uploadVideo(caseId, file) {
  const formData = new FormData();
  formData.append('video_file', file);
  
  const res = await fetch(`${API_URL}/cases/${caseId}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to upload video');
  }
  return res.json();
}

export async function registerRtsp(caseId, url, cameraName) {
  const res = await fetch(`${API_URL}/cases/${caseId}/rtsp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ camera_name: cameraName, rtsp_url: url }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to register RTSP stream');
  }
  return res.json();
}

export async function fetchMatches(caseId) {
  const res = await fetch(`${API_URL}/cases/${caseId}/matches`);
  if (!res.ok) throw new Error('Failed to fetch matches');
  return res.json();
}

export async function fetchJobs(caseId) {
  const res = await fetch(`${API_URL}/cases/${caseId}/jobs`);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  return res.json();
}
