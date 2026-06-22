import React from 'react'
import { PREFERRED_STACK } from '../constants'
import { competitionLabel, formatSalary, highlightKeywords } from '../lib/utils'
import type { Job } from '../types'
// import MatchSection from './MatchSection'

interface DetailPaneProps {
  job: Job | null
  onApply: (job: Job) => void
}

export default function DetailPane({ job, onApply }: DetailPaneProps) {
  if (!job) {
    return (
      <div className="flex-1 flex items-center justify-center bg-parchment">
        <p className="text-[13px] text-chip-text">Select a job to view details</p>
      </div>
    )
  }

  const applyUrl = job.apply_url ?? job.url ?? '#'
  const rawCount = job.applicant_count ?? (job.applicants_count ? Number(job.applicants_count) : null)
  const totalApplicants = rawCount !== 0 ? rawCount : null
  const jdHtml = job.description_html ?? null
  const jdParts = !jdHtml && job.description_text
    ? highlightKeywords(job.description_text, PREFERRED_STACK)
    : null

  function handleApply() {
    window.open(applyUrl, '_blank', 'noopener,noreferrer')
    onApply(job!)
  }

  return (
    <div
      className="flex-1 overflow-y-auto px-6 py-5 bg-parchment"
    >
      {/* Company + title */}
      <p className="text-[12px] text-chip-text mb-0.5">{job.company}</p>
      <h1 className="text-[20px] font-medium text-[#2D2A26] mb-4 leading-snug" style={{ textWrap: 'balance' } as React.CSSProperties}>
        {job.title}
      </h1>

      {/* Meta grid */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 mb-4">
        {job.locations?.length > 0 && (
          <div>
            <p className="text-[12px] text-chip-text mb-0.5">Location</p>
            <p className="text-[14px] text-[#2D2A26]">
              {job.locations.map((loc, i) => (
                <span key={i}>
                  {i > 0 && <span className="mx-1.5 font-bold text-[#1E3A36]">·</span>}
                  {loc}
                </span>
              ))}
            </p>
          </div>
        )}
        {(job.job_type ?? job.employment_type) && (
          <MetaRow label="Job type" value={job.job_type ?? job.employment_type!} />
        )}
        {formatSalary(job) !== '—' && (
          <MetaRow label="Salary" value={formatSalary(job)} />
        )}
        {job.work_type && (
          <MetaRow label="Work type" value={job.work_type} />
        )}
        {(job.seniority ?? job.seniority_level) && (
          <MetaRow label="Seniority" value={job.seniority ?? job.seniority_level!} />
        )}
        {job.yoe_required && (
          <MetaRow label="YOE" value={job.yoe_required} />
        )}
        {(job.sponsors_visa != null || job.visa_status) && (
          <MetaRow
            label="Visa"
            value={
              job.sponsors_visa != null
                ? job.sponsors_visa ? 'Yes' : 'No'
                : job.visa_status!
            }
          />
        )}
      </div>

      {/* Apply button */}
      <button
        onClick={handleApply}
        className="mb-5 px-4 py-1.5 rounded text-[14px] font-medium border border-[#1E3A36] text-[#1E3A36] bg-transparent hover:bg-[#1E3A36] hover:text-white transition-colors duration-150"
      >
        Apply
      </button>

      {/* TODO: re-enable when priority scoring is active
      <div className="mb-5">
        <MatchSection job={job} />
      </div>
      */}

      {/* Applicant stats */}
      {(totalApplicants != null || job.applicants_today != null) && (
        <div
          className="flex gap-6 mb-5 px-4 py-3 rounded-lg text-[12.5px] bg-match-bg"
        >
          <StatCell label="Total applicants" value={String(totalApplicants ?? '—')} />
          <StatCell label="Past day" value={String(job.applicants_today ?? '—')} />
          <StatCell label="Competition" value={competitionLabel(totalApplicants)} />
        </div>
      )}

      {/* JD */}
      {(jdHtml || jdParts) && (
        <div>
          <p className="text-[12px] font-medium text-chip-text mb-2">
            Job description
          </p>
          {jdHtml ? (
            <div
              className="text-[15px] leading-[1.75] text-[#4A4540] jd-html"
              dangerouslySetInnerHTML={{ __html: jdHtml }}
            />
          ) : (
            <p className="text-[15px] leading-[1.75] text-[#4A4540] whitespace-pre-wrap">
              {jdParts!.map((part, i) =>
                part.highlight ? (
                  <strong key={i} style={{ color: '#2E6E78', fontWeight: 600 }}>
                    {part.text}
                  </strong>
                ) : (
                  <span key={i}>{part.text}</span>
                )
              )}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[12px] text-chip-text mb-0.5">{label}</p>
      <p className="text-[14px] text-[#2D2A26]">{value || '—'}</p>
    </div>
  )
}

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[12px] text-chip-text mb-0.5">{label}</p>
      <p className="text-[14px] font-medium text-[#2D2A26]">{value}</p>
    </div>
  )
}
