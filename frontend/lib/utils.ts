import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

const NEXT_PUBLIC_FEEDBACK_ENDPOINT = process.env.NEXT_PUBLIC_FEEDBACK_ENDPOINT;
const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;

export type DomainFeedback = {
  [domain: string]: number | undefined;
};

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// utils.ts
export function handleDomainFeedback(
  domain: string,
  feedback: number,
  setDomainFeedback: React.Dispatch<React.SetStateAction<DomainFeedback>>
) {
  fetch(`${NEXT_PUBLIC_API_URL}/${NEXT_PUBLIC_FEEDBACK_ENDPOINT}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ domain, feedback }),
  })
    .then((response) => {
      if (!response.ok) {
        console.error(`Failed to submit feedback for ${domain}: ${response.status}`);
      }
    })
    .catch((error) => {
      console.error(`Error submitting feedback for ${domain}:`, error);
    });

  setDomainFeedback((prev) => ({ ...prev, [domain]: feedback }));
}




