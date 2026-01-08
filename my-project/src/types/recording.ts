/**
 * Recording-specific types
 */

export interface RecordingState {
  is_recording: boolean;
  audio_chunks: Blob[]; // collected during recording
  duration_seconds: number;
  is_paused: boolean;
  error?: string; // e.g., "microphone_permission_denied"
}

export interface RecordingConfig {
  max_duration_seconds: number; // 300 (5 min)
  mime_type: string; // "audio/webm;codecs=opus" or "audio/mp4"
  audio_bitrate: number; // 64000–128000 bps
  sample_rate: number; // 48000 Hz ideal
}

export interface AudioAnalysis {
  frequencyData: Uint8Array; // Raw frequency bins (0-255 per bin)
  visualBars: number[]; // Aggregated 12 bars for UI (0-255 per bar)
  rmsLevel: number; // RMS energy level (0-1) for volume detection
}
