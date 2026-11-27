/**
 * Parameter pemanggilan sesuai keluarga model. Model gpt-5 ke atas menolak `max_tokens`, dan hanya
 * menerima `temperature` selain 1 bila `reasoning_effort` "none". Model lama menolak `reasoning_effort`.
 */
export function opsiModel(model: string, temperature: number, maksKeluaran: number) {
  if (!/^(gpt-([5-9]|\d{2})|o\d)/.test(model)) return { model, temperature, max_tokens: maksKeluaran };
  return {
    model,
    temperature,
    // Ruang lebih longgar agar JSON tidak terpotong.
    max_completion_tokens: maksKeluaran * 2,
    // Tipe pustaka openai yang terpasang belum mengenal "none".
    reasoning_effort: "none" as unknown as "low",
  };
}
