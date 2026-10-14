# My Bloody Harmonia 🎸🌀

> **Real-Time Audio Chord Recognition & Harmonic Assistant powered by ESP32-S3**

**My Bloody Harmonia** is a compact, standalone hardware device designed for musicians and songwriters. It listens to any musical instrument in real time (via an I2S MEMS microphone or a piezo contact pickup), analyzes its spectral signature using DSP algorithms, and dynamically maps the detected chords onto an interactive **Circle of Fifths** display.

Instead of interrupting your creative workflow with smartphones or computers, *My Bloody Harmonia* provides instant visual feedback and suggests harmonically compatible chord progressions (Pop, Rock, Jazz, etc.) on a sleek circular IPS screen.

---

## ✨ Key Features

* **Universal Audio Input:** Works seamlessly with acoustic/electric guitars, pianos, ukuleles, brass, or vocals.
* **Dual Capture Modes:**
  * **Acoustic (Air):** High-precision digital I2S MEMS microphone (`INMP441`).
  * **Vibrational (Contact):** Piezoelectric pickup input for noisy environments or stage use.
* **Real-Time DSP Engine:**
  * Fast Fourier Transform (FFT) accelerated via ESP32-S3 vector instructions.
  * **Chroma Feature Extraction:** Folds octave frequencies into a 12-bin pitch class profile ($C \rightarrow B$).
  * **Template Matching:** Instantly identifies major/minor triads despite harmonic overtones.
* **Smart Circle of Fifths UI:** Highlights the current root chord along with its 5 diatonic neighbors and suggested style-based progressions.
* **Fully Standalone:** Powered by a rechargeable Li-Po battery with zero external PC/DAW dependencies.

---

## 🛠 Hardware Architecture

* **Microcontroller:** ESP32-S3 DevKit (Dual-core 240 MHz, Vector DSP acceleration)
* **Audio Capture:** INMP441 Digital I2S Microphone / Piezo Sensor Stage
* **Display:** GC9A01 1.28" Circular IPS Display (SPI Interface, $240 \times 240$ px)
* **Controls:** Navigation buttons + Foot-switch support (Freeze/Hold mode)
* **Power Management:** Li-Po battery + TP4056 charging circuit + 3.3V LDO

---

## 👥 Team & Responsibilities

Developed as a course project by a 3-member engineering team:

1. **Hardware & Embedded Systems:** Circuit design, power management, piezo buffer stage, PCB layout, and 3D-printed enclosure.
2. **DSP & Firmware Engineering:** FreeRTOS task scheduling, I2S DMA streaming, FFT implementation, and Chroma Feature extraction algorithm.
3. **UI/UX & Music Theory Logic:** Graphical rendering engine (`TFT_eSPI` / `LVGL`), Circle of Fifths state machine, and chord progression recommendation engine.

---

## 🚀 Getting Started (Development Setup)

### Prerequisites
* [VS Code](https://code.visualstudio.com/) + [PlatformIO IDE Extension](https://platformio.org/)
* C/C++ toolchain for ESP32

### Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/my-bloody-harmonia.git](https://github.com/YOUR_USERNAME/my-bloody-harmonia.git)
   cd my-bloody-harmonia
