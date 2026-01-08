/**
 * UI and navigation types
 */

export type AppView = 'wheel' | 'recording' | 'gallery' | 'content' | 'onboarding';

export interface NavigationState {
  current_screen: AppView;
  current_content_page?: string; // 'how_to_play', 'our_story', etc.
}

export interface UIError {
  id: string;
  message: string;
  type: 'warning' | 'error' | 'critical';
  timestamp: string;
  dismissible: boolean;
}

export interface FeatureFlags {
  enable_photo_upload: boolean;
  enable_topic_pack_switching: boolean;
  enable_analytics: boolean;
  enable_offline_mode: boolean;
}

export interface ContentSection {
  type: 'heading' | 'paragraph' | 'list' | 'image' | 'form' | 'faq';
  content: string | string[] | { src: string; alt: string };
  metadata?: Record<string, any>;
}

export interface ContentPage {
  id: string;
  title: string;
  sections: ContentSection[];
}
