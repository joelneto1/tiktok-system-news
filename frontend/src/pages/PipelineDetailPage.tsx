import { useParams } from 'react-router-dom'

export default function PipelineDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()

  return (
    <div>
      <h1 className="text-2xl font-bold text-text-primary">
        Pipeline - Job {jobId}
      </h1>
      <p className="text-text-secondary mt-2">Em desenvolvimento...</p>
    </div>
  )
}
