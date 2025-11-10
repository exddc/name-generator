import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

function generateUUID(): string {
  // Use crypto.randomUUID if available
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  
  // Fallback UUID v4 generator for older browsers
  const bytes = new Uint8Array(16);
  
  // Use crypto.getRandomValues if available
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i++) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  
  // Convert to UUID string format
  const hex = Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
  
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20, 32)
  ].join('-');
}

export function getAnonRandomId(): string {
  const STORAGE_KEY = 'anon_random_id';
  if (typeof window === 'undefined') {
      return '';
  }

  let anonId = localStorage.getItem(STORAGE_KEY);
  if (!anonId) {
      anonId = 'anon_' + generateUUID();
      localStorage.setItem(STORAGE_KEY, anonId);
  }
  return anonId;
}

export function getDomainRegistrarUrl(domain: string): string {
  // Basic Namecheap
  const url = `https://www.namecheap.com/domains/registration/results/?domain=${encodeURIComponent(domain)}`;
  
  // const affiliateId = process.env.NEXT_PUBLIC_NAMECHEAP_AFFILIATE_ID;
  // const campaignId = 'CAMPAIGN_ID';
  // const adId = 'AD_ID';
  // const url = `https://namecheap.pxf.io/c/${affiliateId}/${campaignId}/${adId}/?u=${encodeURIComponent(
  //   `https://www.namecheap.com/domains/registration/results/?domain=${encodeURIComponent(domain)}`
  // )}`;
  
  return url;
}
