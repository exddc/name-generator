import { Domain, DomainStatus } from "./types";

export const exampleDomains: Domain[] = [
    {
        domain: 'woodcraftstudio.io',
        tld: 'io',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.AVAILABLE,
    },
    {
        domain: 'bauhausmuenchen.com',
        tld: 'com',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.AVAILABLE,
    },
    {
        domain: 'privateview.app',
        tld: 'app',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.AVAILABLE,
    },
    {
        domain: 'beansofsatisfaction.com',
        tld: 'com',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.AVAILABLE,
    },
    {
        domain: 'dailycup.io',
        tld: 'io',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.AVAILABLE,
    },
];

export const exampleRegisteredDomains: Domain[] = [
    {
        domain: 'woodworks.de',
        tld: 'de',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.REGISTERED,
    },
    {
        domain: 'munichfurniture.com',
        tld: 'com',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.REGISTERED,
    },
    {
        domain: 'baumhaus.eu',
        tld: 'eu',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.REGISTERED,
    },
    {
        domain: 'dailycup.com',
        tld: 'com',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DomainStatus.REGISTERED,
    },
];

export const faqQuestions = [
    {
        question: 'What is a domain?',
        answer: 'A domain is the web address you enter in your browser to access a specific website. It replaces the numeric IP addresses that computers use to communicate with each other, making it much easier for people to remember and find websites online.',
    },
    {
        question: 'How do I create a good domain?',
        answer: 'Coming up with a good domain name can be challenging, but it`s worth the time. The name should reflect your brand, be memorable, and avoid confusing elements like hyphens and numbers. Think about whether you need a traditional extension like .com or if a regional or newer extension (like .ca or .xyz) might work better. You can also experiment with free brainstorming or slogan generator tools to spark ideas, then consider registering multiple extensions of the same name to protect your brand in the future.',
    },
    {
        question: 'What is important for a domain name?',
        answer: 'Start by thinking about where your business primarily operates and whether a local extension like .ca or .uk would make sense. Research which extensions your competitors use and look for ways to stand out in your market. If you plan to expand internationally, you may want to secure the .com version as well. It`s also smart to see if matching social media handles are available so your brand name is consistent everywhere.',
    },
    {
        question: 'How do I know if a domain is available?',
        answer: 'Every suggested domain gets checked for availability in real-time. If a domain is already registered, you`ll see that information in the results. If it`s available, you can register it through a domain registrar or website-building platform to secure it for your use.',
    },
    {
        question: 'How do I see if a domain is good?',
        answer: 'A good domain name is usually short, memorable, and easy to spell. Avoid adding numbers or special characters that might cause confusion or typos. Ideally, it matches the brand or business you`re creating and gives people an immediate sense of what they can expect from your site.',
    },
    {
        question: 'Can I change my domain name later?',
        answer: 'Yes, you can register a new domain whenever you like, but keep in mind that changing your primary domain can affect brand recognition, search engine rankings, and user familiarity. It`s usually a good idea to pick a name you`ll want to keep long-term so you don`t confuse your audience or have to rebuild your online presence.',
    },
    {
        question: 'Where do I register a domain name?',
        answer: 'You can register domains through dedicated registrars like GoDaddy or Namecheap, or through website-building platforms like Squarespace or Wix that offer domain registration as part of their service. During registration, you`ll provide contact information and pay an annual fee, which you`ll need to renew to keep ownership of your chosen name.',
    },
    {
        question: 'How important is the domain extension?',
        answer: 'Domain extensions like .com, .org, or country-specific options can influence how your website is perceived. A .com address often signals a global presence, while regional extensions can help you emphasize a local or specialized focus. The key is choosing an extension that aligns with your target audience and long-term goals.',
    },
];