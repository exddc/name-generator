'use server'

export interface DomainResponse {
  domain: string;
  status: string;
}

/**
 * Calls the backend at :8000/suggest with { query: string }
 * Expects an array of DomainResponse objects.
 */
export async function suggestDomains(query: string): Promise<DomainResponse[]> {
  try {
    const response = await fetch('http://0.0.0.0:8000/suggest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch domain suggestions');
    }

    const data = await response.json();
    console.log('Suggested domains:', data);
    return data as DomainResponse[]; // e.g. [{ domain: "abc.com", status: "free" }, ...]
  } catch (error) {
    console.error('Error suggesting domains:', error);
    return [];
  }
}