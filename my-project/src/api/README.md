# Booking API Integration

Complete booking API client with mock server support for development.

## Overview

The API module provides:

- ✅ Type-safe API client for booking operations
- ✅ Mock API for development (no backend needed)
- ✅ Automatic retry logic with exponential backoff
- ✅ Error handling and validation
- ✅ LocalStorage persistence for mock bookings
- ✅ Environment-based configuration

## Quick Start

### 1. Basic Usage

```tsx
import { bookingClient } from '@/api'

// Create a booking
const booking = await bookingClient.createBooking({
  email: 'user@example.com',
  name: 'John Doe',
  date: '2024-02-15',
  message: 'Optional special requests',
})

console.log(booking.confirmationCode) // e.g., "A1B2C3D4"
```

### 2. Using in Components

```tsx
import { useState } from 'react'
import { BookingModal } from '@/components/form'

export function HomePage() {
  const [bookingOpen, setBookingOpen] = useState(false)

  return (
    <>
      <button onClick={() => setBookingOpen(true)}>Book Now</button>

      <BookingModal
        isOpen={bookingOpen}
        onClose={() => setBookingOpen(false)}
        onSuccess={(booking) => {
          console.log('Booking confirmed:', booking)
        }}
      />
    </>
  )
}
```

## Configuration

### Environment Variables

Create `.env.local` from `.env.example`:

```bash
# Enable/disable mock API
VITE_USE_MOCK_API=true

# Real backend URL (used only if VITE_USE_MOCK_API=false)
VITE_API_BASE_URL=http://localhost:3000/api

# Request timeout (milliseconds)
VITE_API_TIMEOUT=10000

# Retry attempts on failure
VITE_API_RETRIES=3
```

### Programmatic Configuration

```tsx
import { BookingClient } from '@/api'

const client = new BookingClient({
  baseUrl: 'https://api.example.com',
  timeout: 15000,
  retries: 5,
  useMock: false, // Force real API even in development
})

const booking = await client.createBooking(data)
```

## API Endpoints

### Create Booking

```typescript
bookingClient.createBooking(data: BookingRequest): Promise<BookingResponse>
```

**Request:**

```typescript
{
  email: string         // Required, valid email
  name: string          // Required, 2+ characters
  date: string          // Required, ISO date format
  message?: string      // Optional
}
```

**Response:**

```typescript
{
  id: string            // Unique booking ID
  email: string
  name: string
  date: string
  message?: string
  createdAt: string     // ISO timestamp
  confirmationCode: string  // e.g., "A1B2C3D4"
}
```

### Get Booking

```typescript
bookingClient.getBooking(id: string): Promise<BookingResponse>
```

Retrieve a booking by ID (mock stores in localStorage).

### Cancel Booking

```typescript
bookingClient.cancelBooking(id: string, reason?: string): Promise<{ success: boolean }>
```

Cancel an existing booking.

## Error Handling

### Error Types

```typescript
import { BookingApiError } from '@/api'

try {
  await bookingClient.createBooking(data)
} catch (error) {
  if (error instanceof BookingApiError) {
    console.log(error.code) // "BOOKING_NOT_FOUND", "400", etc.
    console.log(error.field) // "email" (optional, field-specific)
    console.log(error.message) // Human-readable error message
  }
}
```

### Automatic Retry Logic

The client automatically retries failed requests with exponential backoff:

- **Attempt 1:** Immediate
- **Attempt 2:** 1 second delay (2^0 \* 1000ms)
- **Attempt 3:** 2 second delay (2^1 \* 1000ms)
- **Attempt 4:** 4 second delay (2^2 \* 1000ms)

Retries are skipped for client errors (4xx):

- ❌ Invalid email (400) — fail immediately
- ✅ Server error (500) — retry with backoff
- ✅ Network timeout — retry with backoff

## Mock API Features

### Development Mode

When `VITE_USE_MOCK_API=true`, the client:

- ✅ Simulates 800ms network latency
- ✅ Stores bookings in `localStorage`
- ✅ Generates realistic confirmation codes
- ✅ Logs operations to console with ✓ indicators
- ✅ Persists data across page refreshes

### Example Mock Flow

```
Browser Console:
✓ Mock booking created: {
  id: "BOOK_1734372345678_abc123",
  email: "user@example.com",
  name: "John Doe",
  date: "2024-02-15",
  createdAt: "2024-12-16T19:32:25.678Z",
  confirmationCode: "A1B2C3D4"
}

localStorage:
- booking_ids: ["BOOK_1734372345678_abc123"]
- booking_BOOK_1734372345678_abc123: {...}
```

### Clear Mock Data

```javascript
// In browser console
localStorage.clear()
location.reload()
```

## Production Setup

### Enable Real Backend

1. **Update .env.local:**

```bash
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=https://api.yourdomain.com
```

2. **Implement Backend Endpoint:**

The backend should provide:

```
POST /api/bookings
Content-Type: application/json

{
  email: string
  name: string
  date: string
  message?: string
}

Response:
{
  id: string
  email: string
  name: string
  date: string
  message?: string
  createdAt: string
  confirmationCode: string
}
```

3. **Error Responses:**

```json
{
  "error": {
    "code": "INVALID_EMAIL",
    "message": "Email is already booked",
    "field": "email"
  }
}
```

## Testing

### Unit Tests

```tsx
import { vi } from 'vitest'
import { BookingClient } from '@/api'

test('creates booking successfully', async () => {
  const client = new BookingClient({ useMock: true })

  const booking = await client.createBooking({
    email: 'test@example.com',
    name: 'Test User',
    date: '2024-02-15',
  })

  expect(booking.confirmationCode).toBeDefined()
})

test('retries on network error', async () => {
  const client = new BookingClient({ useMock: false })
  const fetchSpy = vi
    .spyOn(global, 'fetch')
    .mockRejectedValueOnce(new Error('Network error'))
    .mockResolvedValueOnce(new Response(JSON.stringify({ id: '123' }), { status: 200 }))

  const booking = await client.createBooking(data)
  expect(fetchSpy).toHaveBeenCalledTimes(2) // Initial + retry
})
```

### Integration Tests

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BookingModal } from '@/components/form'

test('booking modal submits to API', async () => {
  const onSuccess = vi.fn()

  render(<BookingModal isOpen={true} onClose={() => {}} onSuccess={onSuccess} />)

  // Fill form
  fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
    target: { value: 'test@example.com' },
  })
  fireEvent.change(screen.getByPlaceholderText('Your full name'), {
    target: { value: 'John Doe' },
  })

  // Submit
  fireEvent.click(screen.getByText('Confirm Booking'))

  // Wait for success
  await waitFor(() => {
    expect(screen.getByText(/Your booking has been confirmed/i))
  })

  expect(onSuccess).toHaveBeenCalled()
})
```

## Debugging

### Enable Verbose Logging

```typescript
const client = new BookingClient({
  useMock: true,
})

// Check browser console for:
// ✓ Mock booking created: {...}
// ✓ Mock booking cancelled: BOOK_xxx
```

### Check Mock Data

```javascript
// View all stored bookings in browser console
JSON.parse(localStorage.getItem('booking_ids')).forEach((id) => {
  console.log(JSON.parse(localStorage.getItem(`booking_${id}`)))
})
```

### Network Timeline

```typescript
const startTime = Date.now()
const booking = await bookingClient.createBooking(data)
const duration = Date.now() - startTime

console.log(`Booking created in ${duration}ms`)
// Mock: 800ms (simulated latency)
// Real: varies by network
```

## File Structure

```
src/api/
├── index.ts           # Exports (main entry point)
├── types.ts           # TypeScript types
├── bookingClient.ts   # API client implementation
└── README.md          # This file
```

## TypeScript Support

All components are fully typed:

```typescript
import type { BookingRequest, BookingResponse, ApiError } from '@/api'

const data: BookingRequest = {
  email: 'user@example.com',
  name: 'John Doe',
  date: '2024-02-15',
}

const response: BookingResponse = await bookingClient.createBooking(data)
```

## Next Steps

1. **Implement Backend:** Create Express.js server with `/api/bookings` endpoint
2. **Database:** Set up booking storage (PostgreSQL, MongoDB, etc.)
3. **Email:** Configure confirmation email sending
4. **Analytics:** Track booking conversions
5. **Payment:** Add payment processing if needed
6. **Admin Dashboard:** Build booking management interface

## Support

For issues or questions:

1. Check browser console for mock API logs
2. Verify `.env.local` configuration
3. Test with `/api/README.md` examples
4. Check component integration in `BookingModal`
