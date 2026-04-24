# HOMES Engine: Absolute Cinema Creator

HOMES Engine is an automated video production system designed to generate high-quality, branded content directly from mobile environments. Originally conceived as a challenge to traditional desktop-heavy workflows, the project focuses on orchestrating AI scripting, voice synthesis, and complex FFmpeg rendering within restricted hardware.

## The Vision & History

The project started with a clear objective: proving that professional-grade media automation doesn't require a workstation. Developed using **Acode** as the primary IDE and **Termux** as the execution environment, HOMES Engine was built by finding workarounds for mobile-specific constraints. 

From handling ARM64 architecture limitations to bypassing Android's file system restrictions, every module reflects a "hacker mindset"—optimizing performance where resources are scarce and utilizing system hooks (Termux API) for native features like haptic feedback, notifications, and speech-to-text.

## Technical Stack

The engine is built on a modular Python architecture, ensuring that each component of the pipeline can be scaled or swapped:

- **Core Logic:** Python 3.10+
- **Video Engine:** FFmpeg (Advanced filter graphs for Ken Burns effects, sidechain compression, and SAR standardization).
- **Intelligence:** Google Gemini API (Scriptwriting and visual prompting).
- **Voice (TTS):** Multi-provider support including Edge-TTS, Google TTS, and Gemini-native synthesis.
- **Environment:** Termux (Android Linux layer) with Termux-API integration.
- **Branding:** Custom JSON-based branding kits for consistent visual identities (logos, colors, and style prompts).

## Key Features (v1.8 / v3.0)

- **Absolute Cinema Engine:** A refined FFmpeg pipeline that handles complex B-roll transitions and dynamic overlays.
- **Creator Branding Kits:** Support for multiple profiles. Each brand can have its own color palette, style prompts for AI, and signature assets.
- **Mobile-First Workarounds:** Integrated scripts to handle Android storage paths and system-level notifications upon render completion.
- **Hybrid Input:** Support for manual text entry, clipboard pasting, or voice commands via STT.
- **Autonomous Mode:** A specialized mode designed for queue-based processing (integration ready for n8n/webhooks).

## Project Structure

- `core/`: The heart of the engine. Contains the video maker, TTS handlers, and branding loaders.
- `branding/`: Directory for creator profiles (colors, logos, and style guidelines).
- `assets/`: Local storage for b-rolls, fonts, and generated imagery.
- `scripts/`: Utility tools for benchmarking system performance and verifying environment secrets.
- `queue/`: JSON-based system for asynchronous task management.

## Installation & Setup

While optimized for Termux, HOMES Engine can run on any Linux-based system with FFmpeg installed.

1. **Environment Setup:**
   ```bash
   bash setup.sh
   ```
2. **Configuration:**
   Rename `.env.example` to `.env` and add your `GEMINI_API_KEY`.
3. **Execution:**
   ```bash
   python3 main.py
   ```

## Development Environment

This project is a testament to mobile development. 
- **Editor:** Acode (Android Code Editor).
- **Terminal:** Termux (Linux environment on Android).
- **Hardware:** Tested on ARM64 mobile devices.

The goal remains unchanged: to bridge the gap between simple mobile apps and professional automation tools through surgical code and creative workarounds.

---
*Developed during the Hackatime / Flavortown event by the HOMES Architect.*

### Queue Daemon
To run the engine as a background worker, consuming pending scripts:
```bash
python main.py --daemon
# drop files as scripts/<brand>_<timestamp>.pending.txt
```
