this file will use as the documentation of ardianfe/music-gen-fn-200e:96af46316252ddea4c6614e31861876183b59dce84bad765f38424e87919dd85 model via replicate. 

input schema:
{
  "type": "object",
  "title": "Input",
  "properties": {
    "seed": {
      "type": "integer",
      "title": "Seed",
      "x-order": 13,
      "description": "Seed for random number generator. If None or -1, a random seed will be used."
    },
    "top_k": {
      "type": "integer",
      "title": "Top K",
      "default": 250,
      "x-order": 8,
      "description": "Reduces sampling to the k most likely tokens."
    },
    "top_p": {
      "type": "number",
      "title": "Top P",
      "default": 0,
      "x-order": 9,
      "description": "Reduces sampling to tokens with cumulative probability of p. When set to  `0` (default), top_k sampling is used."
    },
    "prompt": {
      "type": "string",
      "title": "Prompt",
      "x-order": 0,
      "description": "A description of the music you want to generate."
    },
    "duration": {
      "type": "integer",
      "title": "Duration",
      "default": 8,
      "x-order": 2,
      "description": "Duration of the generated audio in seconds."
    },
    "input_audio": {
      "type": "string",
      "title": "Input Audio",
      "format": "uri",
      "x-order": 1,
      "description": "An audio file that will influence the generated music. If `continuation` is `True`, the generated music will be a continuation of the audio file. Otherwise, the generated music will mimic the audio file's melody."
    },
    "temperature": {
      "type": "number",
      "title": "Temperature",
      "default": 1,
      "x-order": 10,
      "description": "Controls the 'conservativeness' of the sampling process. Higher temperature means more diversity."
    },
    "continuation": {
      "type": "boolean",
      "title": "Continuation",
      "default": false,
      "x-order": 3,
      "description": "If `True`, generated music will continue `melody`. Otherwise, generated music will mimic `audio_input`'s melody."
    },
    "output_format": {
      "enum": [
        "wav",
        "mp3"
      ],
      "type": "string",
      "title": "output_format",
      "description": "Output format for generated audio.",
      "default": "wav",
      "x-order": 12
    },
    "continuation_end": {
      "type": "integer",
      "title": "Continuation End",
      "minimum": 0,
      "x-order": 5,
      "description": "End time of the audio file to use for continuation. If -1 or None, will default to the end of the audio clip."
    },
    "continuation_start": {
      "type": "integer",
      "title": "Continuation Start",
      "default": 0,
      "minimum": 0,
      "x-order": 4,
      "description": "Start time of the audio file to use for continuation."
    },
    "multi_band_diffusion": {
      "type": "boolean",
      "title": "Multi Band Diffusion",
      "default": false,
      "x-order": 6,
      "description": "If `True`, the EnCodec tokens will be decoded with MultiBand Diffusion. Only works with non-stereo models."
    },
    "normalization_strategy": {
      "enum": [
        "loudness",
        "clip",
        "peak",
        "rms"
      ],
      "type": "string",
      "title": "normalization_strategy",
      "description": "Strategy for normalizing audio.",
      "default": "loudness",
      "x-order": 7
    },
    "classifier_free_guidance": {
      "type": "integer",
      "title": "Classifier Free Guidance",
      "default": 3,
      "x-order": 11,
      "description": "Increases the influence of inputs on the output. Higher values produce lower-varience outputs that adhere more closely to inputs."
    }
  }
}



output schema:

{
  "type": "string",
  "title": "Output",
  "format": "uri"
}