export type Visibility = 'private' | 'shared';
export type MemoryKind = 'travel' | 'milestone' | 'daily';
export const visibilityLabels: Record<Visibility,string> = {private:'仅自己',shared:'双人共享'};
export const memoryKindLabels: Record<MemoryKind,string> = {travel:'旅行足迹',milestone:'重要时刻',daily:'日常记录'};
export function formatOccurrence(date: string): string {
  const match = date.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[1]}.${match[2]}.${match[3]}` : date;
}
