import { useState } from 'react'
import PipelineForm, { type PipelineFormData } from '@/components/pipeline/PipelineForm'
import JobHistoryTable from '@/components/pipeline/JobHistoryTable'

export default function PipelinePage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  function handleSubmit(_data: PipelineFormData) {
    // PipelineForm already calls the API — just refresh the job history
    setRefreshTrigger((prev) => prev + 1)
  }

  function handleQueue(_data: PipelineFormData) {
    // PipelineForm already calls the API — just refresh the job history
    setRefreshTrigger((prev) => prev + 1)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-10">
        {/* Page header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            <span className="text-text-primary">Criar </span>
            <span className="text-accent">Video</span>
          </h1>
          <p className="mt-1.5 text-sm text-text-secondary">
            Inicie um novo processo de geracao de video com avatar AI.
          </p>
        </div>

        {/* Creation form */}
        <PipelineForm onSubmit={handleSubmit} onQueue={handleQueue} />

        {/* Divider */}
        <div className="border-t border-border" />

        {/* Job history */}
        <JobHistoryTable refreshTrigger={refreshTrigger} />
      </div>
    </div>
  )
}
