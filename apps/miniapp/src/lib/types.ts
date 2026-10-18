export type Visibility = 'private' | 'shared'
export type Scope = 'personal' | 'shared'
export interface User { id: string; nickname: string; space_id: string | null }
export interface Space { id: string; title: string; start_date: string | null; members: { id: string; nickname: string }[] }
export interface Photo { id: string; url: string }
export interface Place { name: string; country_code: string; country_name: string; city: string; latitude?: number | null; longitude?: number | null; coordinate_system: 'wgs84' | 'gcj02'; timezone?: string }
export interface Memory { id: string; title: string; content: string; occurred_on: string; kind: 'travel' | 'milestone' | 'daily'; visibility: Visibility; trip_id: string | null; place: Place | null; photos: Photo[]; author_id: string; author_name: string; created_at: string }
export interface Trip { id: string; title: string; description: string; start_date: string | null; end_date: string | null; visibility: Visibility; author_id: string; memory_count: number }
export interface Anniversary { id: string; title: string; date: string; repeat_yearly: boolean }
export interface Wish { id: string; title: string; description: string; completed: boolean }
export interface Question { id: string; question: string; my_answer: string | null; partner_answer: string | null; both_answered: boolean }
export interface Mood { id: string; day: string; mood: string; note: string; visibility: Visibility; author_id: string; author_name: string }
export interface Habit { id: string; title: string; checkins: string[]; checked_today: boolean }
export interface List<T> { items: T[]; total: number }
export interface Footprints { items: Memory[]; stats: { countries: number; cities: number; places: number; visits: number } }
