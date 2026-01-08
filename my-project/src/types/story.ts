/**
 * Core data types for Story Portal
 * Implements TypeScript interfaces from DATA_MODEL.md
 */

export interface Prompt {
  id: string;
  text: string;
  category?: string;
  declaration_risk: 'low' | 'medium' | 'high';
  facilitation_hint?: string;
  created_at: string; // ISO 8601
}

export interface PhotoMetadata {
  blob: Blob;
  filename: string;
  upload_date: string; // ISO 8601
}

export interface ConsentData {
  verbal_confirmed: boolean;
  email_confirmed?: boolean;
  consent_date: string; // ISO 8601
  consent_version: string;
}

export interface StoryRecord {
  id: string;
  prompt_id: string;
  prompt_text: string;
  audio_blob: Blob;
  audio_duration_seconds: number;
  audio_format: 'audio/webm' | 'audio/mp4';
  created_at: string;
  updated_at: string;
  photo?: PhotoMetadata;
  storyteller_name?: string;
  storyteller_pronouns?: string;
  consent: ConsentData;
  sharing_status: 'private' | 'shared';
  shared_link?: string;
  marked_for_deletion?: boolean;
  deleted_at?: string;
}

export interface TopicPack {
  id: string;
  name: string;
  description?: string;
  prompts: Prompt[];
  created_at: string;
  active: boolean;
}

export interface OnboardingState {
  has_seen_how_to_play: boolean;
  has_seen_consent_explanation: boolean;
  last_onboarding_date: string;
  version: string;
}

export interface AppSettings {
  theme: 'light' | 'dark' | 'system';
  accessibility: {
    prefers_reduced_motion: boolean;
    high_contrast?: boolean;
    enable_captions?: boolean;
  };
  privacy: {
    analytics_enabled: boolean;
    crash_reports_enabled: boolean;
  };
}
