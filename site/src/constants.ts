import type { Filters } from './types'

export const PREFERRED_STACK = ['Python', 'TypeScript', 'Go', 'React', 'Node.js', 'SQL', 'AWS']

export const FAANG = new Set(['Amazon', 'Google', 'Microsoft', 'Meta', 'Apple', 'Nvidia'])

export const LOCATION_OPTIONS = [
  { value: 'boston', label: 'Boston' },
  { value: 'nyc', label: 'NYC' },
  { value: 'sf', label: 'SF' },
  { value: 'seattle', label: 'Seattle' },
  { value: 'remote', label: 'Remote' },
  { value: 'us', label: 'United States' },
]

export const WORK_TYPE_OPTIONS = [
  { value: 'onsite', label: 'Onsite' },
  { value: 'remote', label: 'Remote' },
  { value: 'hybrid', label: 'Hybrid' },
]

export const JOB_TYPE_OPTIONS = [
  { value: 'full-time', label: 'Full-time' },
  { value: 'part-time', label: 'Part-time' },
  { value: 'contract', label: 'Contract' },
]

export const SORT_OPTIONS = [
  { value: 'latest', label: 'Latest' },
  { value: 'match', label: 'Match %' },
  { value: 'competition', label: 'Competition' },
]

export const DEFAULT_FILTERS: Filters = {
  locations: [],
  companyType: 'all',
  workTypes: [],
  jobTypes: [],
  past24h: false,
  sponsorOnly: false,
  sort: 'latest',
}

export const LEVEL_THRESHOLDS = [5, 15, 30, 60, 100]
