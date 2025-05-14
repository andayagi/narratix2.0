# AudioX API Documentation

## Introduction

AudioX is a state-of-the-art Diffusion Transformer model for anything-to-audio generation. This documentation will guide you through using the AudioX API via Cursor AI.

## Resources

- [Research Paper](https://arxiv.org/abs/2503.10522)
- [Project Page](https://zeyuet.github.io/AudioX/)
- [Hugging Face](https://huggingface.co/HKUSTAudio/AudioX)
- [GitHub Repository](https://github.com/ZeyueT/AudioX)

## Getting Started

### Installation

First, install the required Python client:

```bash
pip install gradio_client
```

### Basic Usage

The primary endpoint for generating audio is `/generate_cond`. Here's a basic example:

```python
from gradio_client import Client, handle_file

# Initialize the client
client = Client("Zeyue7/AudioX")

# Generate audio from text prompt
result = client.predict(
    prompt="Ocean waves crashing on a beach",
    seconds_total=10,
    api_name="/generate_cond"
)

print(result)
```

## API Endpoints

### 1. `/generate_cond` - Main Generation Endpoint

This is the primary endpoint for generating audio based on text, video, or audio prompts.

#### Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| prompt | str | Required | Text description of the audio you want to generate |
| negative_prompt | str | None | Text description of what you don't want in the generated audio |
| video_file | filepath | None | Optional video file to use as input for audio generation |
| audio_prompt_file | filepath | None | Optional audio file to use as a reference |
| audio_prompt_path | str | None | Path to an audio prompt |
| seconds_start | float | 0 | Start time for video processing (in seconds) |
| seconds_total | float | 10 | Total duration of generated audio (in seconds) |
| cfg_scale | float | 7 | Classifier-free guidance scale - how strongly to adhere to prompt |
| steps | float | 100 | Number of diffusion steps - higher means better quality but slower |
| preview_every | float | 0 | Generate preview every N steps (0 to disable) |
| seed | str | "-1" | Random seed for reproducibility (-1 for random seed) |
| sampler_type | string | "dpmpp-3m-sde" | Diffusion sampler algorithm |
| sigma_min | float | 0.03 | Minimum noise level |
| sigma_max | float | 500 | Maximum noise level |
| cfg_rescale | float | 0 | CFG rescale amount |
| use_init | bool | False | Whether to use an initial audio input |
| init_audio | filepath | None | Initial audio file to build upon |
| init_noise_level | float | 0.1 | Noise level to apply to initial audio |

#### Returns:

- A tuple containing:
  1. Video output (dict with video and subtitles)
  2. Audio output (filepath)

#### Available Sampler Types:

- "dpmpp-3m-sde" (default)
- "dpmpp-2m-sde"
- "k-heun"
- "k-lms"
- "k-dpmpp-2s-ancestral"
- "k-dpm-2"
- "k-dpm-fast"

## Example Use Cases

### 1. Text-to-Audio Generation

```python
from gradio_client import Client

client = Client("Zeyue7/AudioX")

# Generate nature sounds from text description
result = client.predict(
    prompt="Birds chirping in a forest with a gentle breeze",
    seconds_total=15,
    cfg_scale=8,
    steps=120,
    api_name="/generate_cond"
)

print(f"Audio output file: {result[1]}")
```

### 2. Video-to-Audio Generation

```python
from gradio_client import Client, handle_file

client = Client("Zeyue7/AudioX")

# Generate audio that matches a video
result = client.predict(
    prompt="Epic orchestral soundtrack",
    video_file=handle_file("my_video.mp4"),
    seconds_total=20,
    cfg_scale=7.5,
    steps=150,
    api_name="/generate_cond"
)

print(f"Video with generated audio: {result[0]['video']}")
print(f"Audio output file: {result[1]}")
```

### 3. Audio Modification with Initial Input

```python
from gradio_client import Client, handle_file

client = Client("Zeyue7/AudioX")

# Modify existing audio
result = client.predict(
    prompt="Add thunderstorm effects",
    use_init=True,
    init_audio=handle_file("original_audio.wav"),
    init_noise_level=0.3,
    seconds_total=12,
    api_name="/generate_cond"
)

print(f"Modified audio output: {result[1]}")
```

## Best Practices

1. **Prompt Engineering**:
   - Be specific and detailed in your prompts
   - Use descriptive adjectives
   - Specify sound sources and characteristics

2. **Parameter Tuning**:
   - Use higher step counts (100-200) for better quality
   - Adjust CFG scale between 5-10 (higher values follow prompt more strictly)
   - Experiment with different sampler types for different audio characteristics

3. **Seed Values**:
   - Use specific seed values to get reproducible results
   - Set to -1 for random generation each time

## Troubleshooting

- If you encounter errors, check that file paths are correct and files are valid
- For video files, ensure they are in a supported format (MP4 recommended)
- If results don't match your expectations, try adjusting the CFG scale or providing more detailed prompts

## Advanced Usage

### Accessing Other API Endpoints

The AudioX API also provides several lambda endpoints. These endpoints don't require parameters and return the default settings:

```python
from gradio_client import Client

client = Client("Zeyue7/AudioX")

# Get default parameter values
defaults = client.predict(api_name="/lambda")
print(defaults)
```

## Integration with Cursor AI

When using this API with Cursor AI, you can leverage Cursor's context awareness to generate appropriate prompts and parameters based on your project needs.

### Example Cursor AI Implementation

```python
# Example Cursor AI integration
def generate_audio_for_project(project_context, audio_description):
    """
    Generate audio based on project context and description.
    
    Args:
        project_context: The context from Cursor AI
        audio_description: Description of the audio to generate
        
    Returns:
        Path to generated audio file
    """
    from gradio_client import Client
    
    client = Client("Zeyue7/AudioX")
    
    # Generate context-aware prompt
    enhanced_prompt = f"{audio_description} for {project_context}"
    
    result = client.predict(
        prompt=enhanced_prompt,
        seconds_total=15,
        cfg_scale=7.5,
        steps=120,
        api_name="/generate_cond"
    )
    
    return result[1]  # Return audio file path
```
