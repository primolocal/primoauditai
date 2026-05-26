// PrimoAuditAI Frontend API Configuration
// Centralizes API base URL for all frontend fetch calls

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

/** Build a full API URL from a path */
export const apiUrl = (path: string): string => {
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${API_BASE}${cleanPath}`;
};

/** Wrapper around fetch that injects the API base */
export async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
    return fetch(apiUrl(path), options);
}
