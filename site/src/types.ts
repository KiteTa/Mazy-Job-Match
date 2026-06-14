export interface Job {
  source: string
  id: string | null
  title: string
  company: string
  locations: string[]
  is_remote?: boolean | null
  work_type?: string | null
  job_type?: string | null
  department?: string | null
  url: string | null
  apply_url: string | null
  description_text: string | null
  description_html?: string | null
  published_at: string | null
  posted_at: string | null
  first_published_at?: string | null
  active?: boolean | null
  is_visible?: boolean
  // enriched
  required_skills?: string[]
  tools_and_tech?: string[]
  visa_status?: string | null
  salary_min?: number | null
  salary_max?: number | null
  seniority?: string | null
  yoe_required?: string | null
  applicant_count?: number | null
  applicants_today?: number | null
  sponsors_visa?: boolean | null
  // legacy (github scraper)
  applicants_count?: string | null
  seniority_level?: string | null
  employment_type?: string | null
  workplace_types?: string[]
  salary?: string | null
  country?: string | null
  location?: string | null
}

export interface JobsData {
  date: string
  run_timestamp: string
  stats: {
    total_scraped: number
    after_filters: number
  }
  jobs: Job[]
}

export type SortOption = 'latest' | 'match' | 'competition'

export interface Filters {
  locations: string[]
  companyType: 'all' | 'faang' | 'other'
  workTypes: string[]
  jobTypes: string[]
  past24h: boolean
  sponsorOnly: boolean
  sort: SortOption
}
