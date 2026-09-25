# Landing redesign

Original IP-SAKTI landing page at `/`; the existing dashboard is now `/workspace`. All case, source, privacy and question routes remain available.

Inspiration reviewed: https://github.com/hardikdhingra150/MedBridge/tree/main/frontend/src — specifically Landing.jsx and landing/Hero.jsx. Borrowed only the broad idea of a cinematic product introduction, narrative sections and direct platform entry. No source, assets or section copy were copied.

The new page includes an original emerald/champagne identity, botanical art, interactive jurisdiction comparison, keyboard-operable workflow tabs and a branching workflow diagram, source transparency, FAQs and workspace links. Motion can be paused; OS reduced-motion is respected. No background video or additional animation library is required.

Hero asset: `public/knowledge-leaf.png`, generated with the built-in image-generation tool; conceptual artwork, not botanical identification. Prompt: “Standalone premium website hero artwork for IP-SAKTI, an Ayurveda intellectual property landing page. A cinematic premium 3D editorial macro sculpture symbolizing preserving knowledge: one luminous emerald translucent botanical leaf suspended inside a thin brushed champagne-gold protective circular orbit, tiny mint particles and exquisite fine vein detail, subtle glass optical effects. Deep almost-black forest green background #080f0d. Square, centered sculptural object with generous negative space. Complete orbit visible. Strong dimensional studio spotlight, luminous emerald glass caustics, restrained mint highlights. No text, letters, UI, logos, watermark; conceptual invented botanical form, no real plant identification and no medical claims.”

This landing artwork is an animated raster asset. The dashboard retains its actual interactive Three.js WebGL globe. No fake legal answers or efficacy claims were added. Live backend features remain unconnected.

Validation: production compilation, lint, existing domain/API tests and local HTTP availability. Browser visual/device testing was not requested and has not been performed. Publishing remains blocked pending explicit authorization to upload source to the private preview repository; no upload was retried.
