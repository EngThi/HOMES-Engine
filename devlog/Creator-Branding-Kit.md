# Creator Branding Kit - v1.8 Update

The engine has moved from a generic video generator to a personal studio. I implemented a modular branding system that allows the engine to adopt a specific creator's visual and narrative identity.

### Identity Injection
I added a `BrandingLoader` module that handles custom configurations for different profiles. This includes:
- **Style Prompts**: The engine now injects a "Style Prompt" directly into Gemini. If a creator wants an "aggressive" or "minimalist" tone, the AI writes the script in that specific voice from the start.
- **Brand Colors**: Visual themes are now driven by a `brand_colors.json` file, ensuring consistency across all renders.

### Asset Prioritization
The rendering pipeline was refactored to prioritize local assets over generated ones:
- **Custom B-Roll**: The engine now checks the branding folder for user-provided clips first. It only generates new media if it needs more footage to fill the duration.
- **Automated Overlays**: Implementation of an automated logo overlay in the FFmpeg chain.
- **Signature Music**: Support for specific background tracks, allowing creators to use their signature sound in every video.

This update pushes the project into v1.8, focusing on making the output feel like a professional product rather than a test script.

**Status**: v1.8 Branded Edition operational.
