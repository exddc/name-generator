import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getAnonRandomId(): string {
  const STORAGE_KEY = 'anon_random_id';
  if (typeof window === 'undefined') {
      return '';
  }

  let anonId = localStorage.getItem(STORAGE_KEY);
  if (!anonId) {
      anonId = 'anon_' + crypto.randomUUID();
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
