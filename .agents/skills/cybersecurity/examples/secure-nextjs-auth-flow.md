# Secure Next.js Auth Flow

## Secure Cookie Configuration

```tsx
// Server-side: set session cookie with all protections
import { cookies } from 'next/headers';

export async function setSessionCookie(token: string) {
  cookies().set('session', token, {
    httpOnly: true,        // Not accessible via JavaScript (prevents XSS theft)
    secure: true,          // Only sent over HTTPS
    sameSite: 'lax',       // CSRF protection (strict for highest security)
    path: '/',
    maxAge: 60 * 60 * 24,  // 24 hours — short-lived
  });
}
```

## Content Security Policy

```tsx
// next.config.ts — strict CSP
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'nonce-{NONCE}'",  // No inline scripts without nonce
      "style-src 'self' 'unsafe-inline'",    // Inline styles (needed by most CSS-in-JS)
      "img-src 'self' data: https:",
      "font-src 'self'",
      "connect-src 'self' https://api.yourapp.com",
      "frame-ancestors 'none'",              // Prevent clickjacking
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; '),
  },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
];
```

## Server-Side Auth Check (Middleware)

```tsx
// middleware.ts — protect routes server-side, never client-side only
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const session = request.cookies.get('session')?.value;

  // Protected routes require valid session
  if (request.nextUrl.pathname.startsWith('/dashboard')) {
    if (!session) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
    // Validate token server-side (not just check existence)
  }

  return NextResponse.next();
}
```

## Redirect Validation

```tsx
// Never trust user-controlled redirect URLs
function safeRedirect(url: string | null, fallback = '/'): string {
  if (!url) return fallback;
  // Only allow relative paths — block absolute URLs (phishing)
  if (url.startsWith('/') && !url.startsWith('//')) return url;
  return fallback;
}

// Usage after login:
const redirectTo = safeRedirect(searchParams.get('redirect'));
redirect(redirectTo);
```
