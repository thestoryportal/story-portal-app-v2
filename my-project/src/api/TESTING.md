# Booking API Integration Testing Guide

Complete guide for testing the booking form and API integration.

## Quick Test Flow

### 1. Start Development Server

```bash
pnpm dev
# Open http://localhost:5173
```

### 2. Open Browser Console

Press `F12` or `Cmd+Option+I` to open DevTools, go to **Console** tab.

### 3. Test Booking Form

#### Option A: Using BookingModal Component

```javascript
// In any React component that uses BookingModal
<BookingModal isOpen={true} onClose={() => {}} />
```

Then fill the form:

1. **Name:** "John Doe"
2. **Email:** "john@example.com"
3. **Date:** "2024-02-15"
4. **Message:** "Please set up near the main stage"
5. Click **Confirm Booking**

#### Option B: Direct API Test

```javascript
// Test in browser console
const { bookingClient } = await import('/src/api/index.ts')

// Create booking
const booking = await bookingClient.createBooking({
  email: 'test@example.com',
  name: 'Test User',
  date: '2024-02-15',
  message: 'Test message',
})

console.log('Booking created:', booking)
// Output:
// {
//   id: "BOOK_1734372345678_abc123",
//   email: "test@example.com",
//   name: "Test User",
//   date: "2024-02-15",
//   message: "Test message",
//   createdAt: "2024-12-16T19:32:25.678Z",
//   confirmationCode: "A1B2C3D4"
// }
```

## Expected Behavior

### Mock API (Development)

**Console Output:**

```
✓ Mock booking created: {
  id: "BOOK_1734372345678_abc123",
  email: "test@example.com",
  name: "Test User",
  date: "2024-02-15",
  message: "Test message",
  createdAt: "2024-12-16T19:32:25.678Z",
  confirmationCode: "A1B2C3D4"
}
```

**Success Message:**

- Green checkmark (✓)
- "Thank you, Test User! Your booking has been confirmed."
- Confirmation code displayed: `A1B2C3D4`
- Modal closes after 3 seconds

**Data Persistence:**

```javascript
// Check localStorage in DevTools (Application > Local Storage)
localStorage.getItem('booking_ids')
// Output: ["BOOK_1734372345678_abc123"]

localStorage.getItem('booking_BOOK_1734372345678_abc123')
// Output: {"id":"BOOK_1734372345678_abc123",...}
```

## Test Cases

### 1. Validation Tests

#### Empty Form

```
Expected: All fields show error messages
- "Name is required"
- "Email is required"
- "Date is required"
```

#### Invalid Email

```
Email: "notanemail"
Expected Error: "Please enter a valid email address"
```

#### Name Too Short

```
Name: "J"
Expected Error: "Name must be at least 2 characters"
```

#### Valid Form

```
Name: "John Doe"
Email: "john@example.com"
Date: "2024-02-15"
Expected: Form submits successfully
```

### 2. Error Clearing

```
1. Type invalid email: "notanemail"
2. See error: "Please enter a valid email address"
3. Continue typing: "notanemail@example.com"
4. Error disappears immediately
Expected: Real-time validation feedback
```

### 3. Loading State

```
1. Fill valid form
2. Click "Confirm Booking"
3. Button shows "Loading..."
4. Button is disabled
5. After 800ms, success message appears
Expected: 800ms simulated network latency
```

### 4. Success Flow

```
1. Submit valid booking
2. See success message with checkmark
3. Confirmation code displays
4. Modal auto-closes after 3 seconds
Expected: Smooth success UX with confirmation
```

## Advanced Testing

### Test Data Retrieval

```javascript
// Get booking by ID
const booking = await bookingClient.getBooking('BOOK_1734372345678_abc123')
console.log('Retrieved:', booking)
```

### Test Booking Cancellation

```javascript
// Cancel booking
const result = await bookingClient.cancelBooking('BOOK_1734372345678_abc123', 'Changed my mind')
console.log('Cancelled:', result) // { success: true }

// Verify it's deleted
try {
  await bookingClient.getBooking('BOOK_1734372345678_abc123')
} catch (error) {
  console.log('Booking not found:', error.message)
}
```

### Check All Bookings

```javascript
// View all bookings in localStorage
const ids = JSON.parse(localStorage.getItem('booking_ids') || '[]')
const bookings = ids.map((id) => JSON.parse(localStorage.getItem(`booking_${id}`)))
console.table(bookings)
```

### Clear Test Data

```javascript
// Reset localStorage for clean testing
localStorage.clear()
location.reload()
```

## Network Simulation

### Simulate Slow Network

```javascript
// Edit BookingClient config temporarily
// In src/api/bookingClient.ts:
// Change: setTimeout(() => { ... }, 800)
// To: setTimeout(() => { ... }, 3000) // 3 second delay
```

### Simulate API Error

```javascript
// Temporarily modify mock API to throw error
// In bookingClient.ts, in mockCreateBooking():
// throw new BookingApiError('SERVER_ERROR', undefined, 'Server error')
```

## Form Submission Flow

### Complete Test Scenario

```javascript
// 1. Reset data
localStorage.clear()

// 2. Import components
import { BookingModal } from '/src/components/form/index.ts'

// 3. Render (in React component or test)
;<BookingModal isOpen={true} onClose={() => console.log('closed')} />

// 4. Fill form
// Name: "Alice Smith"
// Email: "alice@example.com"
// Date: "2024-03-20"
// Message: "Interested in VIP experience"

// 5. Submit
// Click "Confirm Booking"

// 6. Verify success
// ✓ Check console for "Mock booking created"
// ✓ Check for green success message
// ✓ Check for confirmation code
// ✓ Verify localStorage has booking_ids
// ✓ Modal closes automatically

// 7. Check browser DevTools > Application > Local Storage
// booking_ids: ["BOOK_..."]
// booking_BOOK_...: { ... booking data ... }
```

## Chrome DevTools Integration

### Network Tab

1. Open DevTools → **Network** tab
2. Fill and submit booking form
3. **Mock API:** No network requests (all in localStorage)
4. **Real API:** See POST request to `/api/bookings`

### Storage Tab

1. Open DevTools → **Application** → **Local Storage**
2. Select current site
3. See keys: `booking_ids`, `booking_BOOK_*`
4. Click each to view booking data

### Console Tab

1. Open DevTools → **Console** tab
2. See ✓ log when booking created
3. See error messages if validation fails
4. Test API directly with JavaScript

## Troubleshooting

### Booking Not Appearing

**Issue:** Form submits but no success message

**Debug Steps:**

```javascript
// Check console for errors
window.addEventListener('error', (e) => console.error('Error:', e))

// Verify API client is initialized
import { bookingClient } from '/src/api'
console.log('Client:', bookingClient)

// Test manual creation
const booking = await bookingClient.createBooking({
  email: 'test@example.com',
  name: 'Test',
  date: '2024-02-15',
})
console.log('Manual test:', booking)
```

### Confirmation Code Not Showing

**Issue:** Success message but no confirmation code

**Check:**

```javascript
// Verify booking response has confirmationCode
const booking = await bookingClient.createBooking(data)
console.log('Code:', booking.confirmationCode) // Should be defined
```

### Data Persisting Across Reloads

**Expected:** Data persists after page reload
**If not working:** Check localStorage is enabled

```javascript
// Test localStorage
localStorage.setItem('test', 'value')
console.log(localStorage.getItem('test')) // Should output: "value"
```

## Performance Testing

### Measure API Response Time

```javascript
const start = performance.now()
const booking = await bookingClient.createBooking(data)
const duration = performance.now() - start

console.log(`API call took ${duration.toFixed(0)}ms`)
// Expected mock: ~800ms (simulated latency)
```

### Test Under Network Throttling

1. Open DevTools → **Network** tab
2. Click throttle dropdown (usually "No throttling")
3. Select "Slow 3G" or custom throttle
4. Submit form
5. Watch for 3+ second delay

## Integration Test Example

```typescript
// src/__tests__/bookingForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BookingModal } from '@/components/form'
import { vi } from 'vitest'

test('booking form submits and shows success', async () => {
  const onSuccess = vi.fn()

  render(
    <BookingModal
      isOpen={true}
      onClose={() => {}}
      onSuccess={onSuccess}
    />
  )

  // Fill form
  fireEvent.change(screen.getByPlaceholderText('Your full name'), {
    target: { value: 'John Doe' }
  })
  fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
    target: { value: 'john@example.com' }
  })
  fireEvent.change(screen.getByDisplayValue(''), { // date input
    target: { value: '2024-02-15' }
  })

  // Submit
  fireEvent.click(screen.getByText('Confirm Booking'))

  // Wait for success
  await waitFor(() => {
    expect(screen.getByText(/Your booking has been confirmed/i))
  })

  // Verify callback
  expect(onSuccess).toHaveBeenCalled()
})
```

## Production Testing

When switching to real backend:

1. **Update .env.local:**

```bash
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=https://your-api.com
```

2. **Test Real Endpoint:**

```javascript
// Test API is accessible
fetch('https://your-api.com/bookings', { method: 'POST' })
  .then((r) => r.json())
  .catch((e) => console.error('API Error:', e))
```

3. **Monitor:**
   - Check API logs for booking requests
   - Verify database entries
   - Test error responses
   - Monitor response times

## Checklist

- [ ] Form validates on empty submit
- [ ] Form validates email format
- [ ] Form validates name length
- [ ] Form validates date field
- [ ] Errors clear on user input
- [ ] Loading state shows during submit
- [ ] Success message displays after 800ms
- [ ] Confirmation code displays
- [ ] Modal closes after 3 seconds
- [ ] Data persists in localStorage
- [ ] Can retrieve booking by ID
- [ ] Can cancel booking
- [ ] All fields populated correctly
