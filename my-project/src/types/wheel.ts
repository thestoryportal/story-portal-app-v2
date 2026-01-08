/**
 * Wheel-specific types
 */

import type { Prompt } from './story';

export interface WheelState {
  current_prompt: Prompt | null;
  current_topic_pack_id: string;
  last_spin_timestamp: string | null;
  pass_count: number; // 0, 1, or 2 (2 = locked in)
  is_spinning: boolean;
  landed_prompt_index: number | null;
}

export interface WheelPhysics {
  initial_velocity: number; // degrees/millisecond
  friction: number; // 0–1 deceleration factor
  snap_threshold: number; // degrees to snap to prompt
  min_spin_duration: number; // milliseconds
}

export interface WheelConfig {
  prompts_per_wheel: number;
  segment_size_degrees: number;
  damping_factor: number;
  friction_factor: number;
  min_spin_duration_ms: number;
  snap_duration_ms: number;
}
