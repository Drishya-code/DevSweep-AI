import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

export function getRiskColor(risk: 'SAFE' | 'CAUTION' | 'DANGEROUS'): string {
  switch (risk) {
    case 'SAFE': return 'text-devsweep-success bg-devsweep-success/10 border-devsweep-success/20'
    case 'CAUTION': return 'text-devsweep-warning bg-devsweep-warning/10 border-devsweep-warning/20'
    case 'DANGEROUS': return 'text-devsweep-danger bg-devsweep-danger/10 border-devsweep-danger/20'
  }
}

export function getRiskIcon(risk: 'SAFE' | 'CAUTION' | 'DANGEROUS'): string {
  switch (risk) {
    case 'SAFE': return '✓'
    case 'CAUTION': return '⚠'
    case 'DANGEROUS': return '✕'
  }
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
}