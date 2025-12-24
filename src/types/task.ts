// Task 타입 정의
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';
export type TaskSource = 'manual' | 'slack' | 'confluence' | 'email' | 'other';

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  source: TaskSource;
  sourceReference?: string; // 원본 메시지/문서 ID
  assignedAgentId?: string; // 할당된 Agent ID
  autoAssign?: boolean; // Task별 자동 할당 여부
  dueDate?: Date;
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
}

export interface CreateTaskInput {
  title: string;
  description: string;
  priority?: TaskPriority;
  source?: TaskSource;
  sourceReference?: string;
  dueDate?: Date;
  tags?: string[];
  autoAssign?: boolean;
}

