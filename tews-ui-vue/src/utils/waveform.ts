export const downsampleWaveform = (data: number[], originalFrequency: number, targetFrequency: number) => {
  if (targetFrequency >= originalFrequency) {
    return { downsampledData: data, downsampleFactor: 1 }
  }

  const downsampleFactor = originalFrequency / targetFrequency
  if (!Number.isInteger(downsampleFactor)) {
    throw new Error('Downsample factor must be an integer.')
  }

  const downsampledData: number[] = []
  for (let i = 0; i < data.length; i += downsampleFactor) {
    downsampledData.push(data[i])
  }

  return { downsampledData, downsampleFactor }
}
