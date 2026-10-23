// Runs on the audio thread: hands each small block of mic samples to the page.
class Tap extends AudioWorkletProcessor {
  process(inputs) {
    const samples = inputs[0][0];
    if (samples) this.port.postMessage(samples.slice(0));
    return true;
  }
}

registerProcessor("tap", Tap);
