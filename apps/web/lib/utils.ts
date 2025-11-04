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
