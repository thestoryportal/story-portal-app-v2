import { describe, it, expect } from 'vitest'

describe('Test Setup', () => {
  it('should run tests correctly', () => {
    expect(true).toBe(true)
  })

  it('should have access to DOM matchers', () => {
    const div = document.createElement('div')
    div.textContent = 'Story Portal'
    expect(div).toHaveTextContent('Story Portal')
  })
})
