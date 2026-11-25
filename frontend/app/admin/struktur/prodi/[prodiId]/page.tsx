import { ProdiDetail } from '@/components/admin/prodi-detail'

export default async function ProdiDetailPage({ params }: { params: Promise<{ prodiId: string }> }) {
  const { prodiId } = await params
  return <ProdiDetail prodiId={prodiId} />
}
