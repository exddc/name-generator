import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

const NEXT_PUBLIC_FEEDBACK_ENDPOINT = process.env.NEXT_PUBLIC_FEEDBACK_ENDPOINT;
const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function handleDomainFeedback(domain: string, feedback: boolean, setDomainFeedback: (callback: (prev: any) => any) => void) {
  fetch(`${NEXT_PUBLIC_API_URL}/${NEXT_PUBLIC_FEEDBACK_ENDPOINT}`, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({ domain, feedback }),
  });

  setDomainFeedback((prev) => ({ ...prev, [domain]: feedback }));
};