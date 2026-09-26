import soundFile from '@src/assets/sound/ding.mp3'
import { WSEvent } from '@src/types/ws-event'

export function playAlarmSound() {
  const audio = new Audio(soundFile)
  // audio.addEventListener('ended', props.onEnded)
  // audio.addEventListener('play', props.onPlay)
  audio.play()
}

export function speakAlarm(event: WSEvent) {
  try {
    playAlarmSound()
    const { sub_region, region } = event
    const utterance = new SpeechSynthesisUtterance()

    const voices = window.speechSynthesis.getVoices()
    const bahasaVoice = voices.find((voice) => voice.lang === 'id-ID')

    if (bahasaVoice) {
      utterance.text = `Terdeteksi gempa di ${sub_region}, ${region}`
      utterance.lang = 'id-ID'
      utterance.voice = bahasaVoice
    } else {
      utterance.text = `An earthquake was detected in ${sub_region}, ${region}`
      utterance.lang = 'en-EN'
    }

    window.speechSynthesis.speak(utterance)
  } catch (e) {
    console.log('speak alarm failed', e)
  }
}
