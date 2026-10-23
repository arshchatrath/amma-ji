// Plays Amma ji's voice while it is still arriving: each piece of raw 16-bit audio is turned
// into a tiny AudioBuffer and queued right after the previous one, so there are no gaps.
export function playStream(response, context, { onStart } = {}) {
  const rate = Number(response.headers.get("X-Sample-Rate")) || 24000;
  const reader = response.body.getReader();
  const sources = [];
  let nextTime = 0;
  let leftover = null;
  let stopped = false;

  async function pump() {
    for (;;) {
      const { done, value } = await reader.read();
      if (done || stopped) break;
      let bytes = value;
      if (leftover) {
        bytes = new Uint8Array(leftover.length + value.length);
        bytes.set(leftover);
        bytes.set(value, leftover.length);
        leftover = null;
      }
      if (bytes.length % 2) {
        leftover = bytes.slice(-1); // half a sample: keep it for the next piece
        bytes = bytes.slice(0, -1);
      }
      if (!bytes.length) continue;
      const pcm = new Int16Array(bytes.buffer, bytes.byteOffset, bytes.length / 2);
      const buffer = context.createBuffer(1, pcm.length, rate);
      const channel = buffer.getChannelData(0);
      for (let i = 0; i < pcm.length; i++) channel[i] = pcm[i] / 32768;
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);
      if (!nextTime) {
        nextTime = context.currentTime + 0.05;
        onStart?.();
      }
      source.start(Math.max(nextTime, context.currentTime));
      nextTime = Math.max(nextTime, context.currentTime) + buffer.duration;
      sources.push(source);
    }
    // Wait for the last queued piece to finish playing
    const wait = Math.max(0, nextTime - context.currentTime);
    if (!stopped) await new Promise((r) => setTimeout(r, wait * 1000));
  }

  return {
    done: pump(),
    stop() {
      stopped = true;
      reader.cancel().catch(() => {});
      sources.forEach((s) => {
        try {
          s.stop();
        } catch {
          // already finished
        }
      });
    },
  };
}
