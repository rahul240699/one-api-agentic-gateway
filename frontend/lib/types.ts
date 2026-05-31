// Shared types for the chat/stream UI.

export type MessageRole = "user" | "assistant" | "tool" | "thinking" | "error";

export interface ToolCallCard {
  tool: string;
  provider: string;
  cost: number;
  remainingCredits?: number;
  data?: Record<string, unknown>;
  status: "running" | "done" | "error";
  errorMessage?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text?: string;
  toolCard?: ToolCallCard;
  balanceAfter?: number;
}
