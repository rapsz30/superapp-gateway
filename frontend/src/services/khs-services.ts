import { mockKhsResponse } from '@/src/mocks/khs'
import type { KhsMockResponse } from '@/src/types/khs'

export interface KhsService {
  processDocument(file: File): Promise<KhsMockResponse>
}

export const mockKhsService: KhsService = {
  async processDocument() {
    await new Promise((resolve) => setTimeout(resolve, 1400))
    return structuredClone(mockKhsResponse)
  },
}
