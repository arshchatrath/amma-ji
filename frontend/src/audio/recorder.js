// Records one thing the cook says. Stops by itself after 0.8 s of quiet, or when
// stop() is called. Returns a WAV file (mono, 16 kHz), which is what Gnani's STT wants.
const TARGET_RATE = 16000;

export async function startRecording(context, { silenceMs = 800, maxMs = 15000, waitMs = 7000 } = {}) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
  });
  // The worklet lives in public/ as a plain file, which every browser (Safari too) can load
  await context.audioWorklet.addModule(`${import.meta.env.BASE_URL}tap-worklet.js`);
  const source = context.createMediaStreamSource(stream);
  const tap = new AudioWorkletNode(context, "tap");
  const mute = context.createGain();
  mute.gain.value = 0; // keeps the tap running without playing the mic back
  source.connect(tap).connect(mute).connect(context.destination);

  const blocks = [];
  const started = performance.now();
  let noise = 0.01;
  let heardAt = 0;
  let quietSince = 0;
  let finish;
  const finished = new Promise((resolve) => (finish = resolve));

  tap.port.onmessage = ({ data }) => {
    blocks.push(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
    const level = Math.sqrt(sum / data.length);
    const now = performance.now();
    // Learn how loud the kitchen is in the first moments, then listen for speech above it
    if (now - started < 300) noise = Math.max(noise, level);
    const speaking = level > Math.max(0.02, noise * 2.5);
    if (speaking) {
      heardAt ||= now;
      quietSince = 0;
    } else if (heardAt) {
      quietSince ||= now;
    }
    const doneTalking = heardAt && quietSince && now - quietSince > silenceMs;
    const tooLong = now - started > maxMs;
    const nothingSaid = !heardAt && now - started > waitMs;
    if (doneTalking || tooLong || nothingSaid) finish();
  };

  async function wrapUp() {
    tap.port.onmessage = null;
    source.disconnect();
    tap.disconnect();
    stream.getTracks().forEach((t) => t.stop()); // mic light goes off
    if (!heardAt) return null;
    return toWav(downsample(blocks, context.sampleRate), TARGET_RATE);
  }

  return {
    // resolves with the WAV (or null if nothing was said) once recording ends
    result: finished.then(wrapUp),
    stop: () => finish(),
  };
}

function downsample(blocks, rate) {
  const total = blocks.reduce((n, b) => n + b.length, 0);
  const input = new Float32Array(total);
  let offset = 0;
  for (const b of blocks) {
    input.set(b, offset);
    offset += b.length;
  }
  const ratio = rate / TARGET_RATE;
  const out = new Float32Array(Math.floor(total / ratio));
  for (let i = 0; i < out.length; i++) {
    // average the input samples that fall into this output sample
    const from = Math.floor(i * ratio);
    const to = Math.min(total, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = from; j < to; j++) sum += input[j];
    out[i] = sum / Math.max(1, to - from);
  }
  return out;
}

function toWav(samples, rate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (at, s) => [...s].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)));
  text(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // plain PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}
