export const getMagnitudeWidth = (magnitude: number) => magnitude * 5

export const getDepthColor = (depth: number) => {
  if (depth < 50) return '#FF0000'
  if (depth < 100) return '#FF7A00'
  if (depth < 250) return '#FFE500'
  if (depth < 600) return '#24FF00'
  return '#0500FF'
}
