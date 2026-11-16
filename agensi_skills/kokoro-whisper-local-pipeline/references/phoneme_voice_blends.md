# Voice Blend Catalog: Kokoro ONNX

Kokoro supports linear vector blending between speaker embeddings, producing unique custom voices without fine-tuning:

### Tested Blend Recipes
- **Warm Executive (70% af_heart + 30% af_bella)**:
  - Base tone: Warm, empathetic, professional.
  - Formula: `blend_voices(af_heart, af_bella, weight_a=0.7)`
- **Dynamic Assistant (60% am_adam + 40% am_michael)**:
  - Base tone: Authoritative, energetic, crisp consonants.
  - Formula: `blend_voices(am_adam, am_michael, weight_a=0.6)`
- **Spanish Naturalist (80% ef_dora + 20% em_alex)**:
  - Base tone: Fluid conversational Spanish with balanced pitch.
  - Formula: `blend_voices(ef_dora, em_alex, weight_a=0.8)`

