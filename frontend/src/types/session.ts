export interface Session {
  id: string;
  title: string;
  createdAt: Date;
  messageCount: number;
  totalSaving?: number;
}
