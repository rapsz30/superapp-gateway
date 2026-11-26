import { DetailJudulTa } from '@/components/dosen/detail-judul-ta'

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <DetailJudulTa id={id} />
}
