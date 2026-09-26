export function bandpassFilter(
  inputSignal: number[],
  sampleRate: number,
  lowCutoff: number,
  highCutoff: number,
  order: number = 2
): number[] {
  const nyquist = 0.5 * sampleRate
  const lowW = lowCutoff / nyquist
  const highW = highCutoff / nyquist

  // Calculate filter coefficients
  const [b, a] = calculateButterworth(order, [lowW, highW])

  // Apply the filter
  return applyFilter(inputSignal, b, a)
}

function calculateButterworth(order: number, cutoff: number[]): [number[], number[]] {
  // This is a simplified implementation and may not be as accurate as specialized DSP libraries
  const [lowW, highW] = cutoff
  const b: number[] = new Array(2 * order + 1).fill(0)
  const a: number[] = new Array(2 * order + 1).fill(0)

  const w0 = Math.sqrt(lowW * highW)
  const bw = highW - lowW

  for (let i = 0; i <= 2 * order; i++) {
    const omega = ((i - order) * Math.PI) / order
    const y = 1 / (1 + Math.pow(Math.tan(bw / 2) * Math.cos(omega), 2))
    b[i] = Math.sqrt(y) * Math.pow(w0, i)
    a[i] = y * Math.pow(w0, order - i)
  }

  return [b, a]
}

function applyFilter(inputSignal: number[], b: number[], a: number[]): number[] {
  const outputSignal: number[] = new Array(inputSignal.length).fill(0)
  const order = b.length - 1

  for (let n = 0; n < inputSignal.length; n++) {
    let sum = 0
    for (let k = 0; k <= order; k++) {
      if (n - k >= 0) {
        sum += b[k] * inputSignal[n - k]
      }
    }
    for (let k = 1; k <= order; k++) {
      if (n - k >= 0) {
        sum -= a[k] * outputSignal[n - k]
      }
    }
    outputSignal[n] = sum / a[0]
  }

  return outputSignal
}

// // Example usage:
// const inputSignal: number[] = [
//   /* your input waveform data */
// ]
// const sampleRate = 44100 // Hz
// const lowCutoff = 500 // Hz
// const highCutoff = 2000 // Hz
// const order = 4

// const filteredSignal = bandpassFilter(inputSignal, sampleRate, lowCutoff, highCutoff, order)
