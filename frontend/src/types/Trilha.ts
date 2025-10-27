export type Trilha = {
  id: number;
  name: string;
  thumbnail_url: string;
  author?: string;
  review?: number;          // 0..5
  review_count?: number;
  botaoLabel?: string;      // opcional
  description?: string | null;
  requirements?: string[];  
  targetAudience?: string[]; 
  includedItems?: string[];
  progress_percent?: number;
  status?: string;
  completed_at?: string;
  is_completed?: boolean;
  nextAction?: string;
};
