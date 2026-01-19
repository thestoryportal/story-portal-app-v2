/**
 * RecordingView - Story recording interface
 *
 * Placeholder component for story recording functionality.
 * TODO: Implement full recording interface with audio/video capture.
 */

import { useState } from 'react'
import type { Prompt, StoryRecord } from '../../types/story'

export interface RecordingViewProps {
  prompt: Prompt
  onSaveStory: (story: StoryRecord) => void
  onCancel: () => void
}

export function RecordingView({ prompt, onSaveStory, onCancel }: RecordingViewProps) {
  const [storyText, setStoryText] = useState('')
  const [isRecording, setIsRecording] = useState(false)

  const handleSave = async () => {
    if (!storyText.trim()) {
      alert('Please enter your story before saving.')
      return
    }

    // Create a placeholder audio blob (text-to-speech or silent audio)
    // TODO: Replace with actual audio recording when implemented
    const placeholderAudioBlob = new Blob(
      [new ArrayBuffer(0)],
      { type: 'audio/webm' }
    )

    const now = new Date().toISOString()

    const story: StoryRecord = {
      id: Date.now().toString(),
      prompt_id: typeof prompt === 'string' ? prompt : prompt.id,
      prompt_text: typeof prompt === 'string' ? prompt : prompt.text,
      audio_blob: placeholderAudioBlob,
      audio_duration_seconds: 0,
      audio_format: 'audio/webm',
      created_at: now,
      updated_at: now,
      consent: {
        verbal_confirmed: true,
        consent_date: now,
        consent_version: '1.0',
      },
      sharing_status: 'private',
      // Optional: Store text in storyteller_name field temporarily
      // This is a workaround until proper text story support is added
      storyteller_name: storyText.substring(0, 100),
    }

    onSaveStory(story)
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: '#1a0f08',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      zIndex: 1000,
    }}>
      <div style={{
        maxWidth: '800px',
        width: '100%',
        backgroundColor: '#2a1810',
        borderRadius: '12px',
        padding: '2rem',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.8)',
      }}>
        <h2 style={{ color: '#d4af37', marginBottom: '1rem' }}>
          Record Your Story
        </h2>

        <div style={{
          color: '#f5e6d3',
          marginBottom: '1.5rem',
          padding: '1rem',
          backgroundColor: '#1a0f08',
          borderRadius: '8px',
          borderLeft: '4px solid #d4af37',
        }}>
          <strong>Prompt:</strong> {typeof prompt === 'string' ? prompt : prompt.text}
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{
            display: 'block',
            color: '#d4af37',
            marginBottom: '0.5rem',
            fontWeight: 'bold',
          }}>
            Your Story:
          </label>
          <textarea
            value={storyText}
            onChange={(e) => setStoryText(e.target.value)}
            placeholder="Type your story here..."
            style={{
              width: '100%',
              minHeight: '200px',
              padding: '1rem',
              fontSize: '16px',
              backgroundColor: '#1a0f08',
              color: '#f5e6d3',
              border: '2px solid #8b6f47',
              borderRadius: '8px',
              resize: 'vertical',
              fontFamily: 'inherit',
            }}
          />
        </div>

        {/* Recording status indicator (placeholder for future functionality) */}
        {isRecording && (
          <div style={{
            marginBottom: '1rem',
            padding: '0.5rem 1rem',
            backgroundColor: '#8b2e1c',
            color: '#fff',
            borderRadius: '8px',
            textAlign: 'center',
          }}>
            🔴 Recording in progress... (Feature coming soon)
          </div>
        )}

        <div style={{
          display: 'flex',
          gap: '1rem',
          justifyContent: 'flex-end',
        }}>
          <button
            onClick={onCancel}
            style={{
              padding: '0.75rem 2rem',
              fontSize: '16px',
              backgroundColor: '#4a3830',
              color: '#f5e6d3',
              border: '2px solid #8b6f47',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#5a4840'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#4a3830'
            }}
          >
            Cancel
          </button>

          <button
            onClick={handleSave}
            disabled={!storyText.trim()}
            style={{
              padding: '0.75rem 2rem',
              fontSize: '16px',
              backgroundColor: storyText.trim() ? '#d4af37' : '#6b6b6b',
              color: '#1a0f08',
              border: 'none',
              borderRadius: '8px',
              cursor: storyText.trim() ? 'pointer' : 'not-allowed',
              fontWeight: 'bold',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              if (storyText.trim()) {
                e.currentTarget.style.backgroundColor = '#c4942e'
              }
            }}
            onMouseLeave={(e) => {
              if (storyText.trim()) {
                e.currentTarget.style.backgroundColor = '#d4af37'
              }
            }}
          >
            Save Story
          </button>
        </div>

        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          backgroundColor: '#1a0f08',
          borderRadius: '8px',
          color: '#8b6f47',
          fontSize: '0.875rem',
        }}>
          <strong>Note:</strong> Audio/video recording functionality is planned for a future update.
          For now, you can type your story in the text area above.
        </div>
      </div>
    </div>
  )
}
