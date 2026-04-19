# Video to Documentation Transcoder (Experiment)

Do you have recorded Zoom or Teams calls containing useful information, and you don't want to watch a video to find the information you need? Tired of useful data being trapped inside opaque data formats? This will help you migrate that knowledge.

## Prerequisites

* macOS running on an Apple silicon M-class chip
* [Homebrew](https://brew.sh)
* Python 3.13+
* uv
* ffmpeg
* A [HuggingFace User Access Token](https://huggingface.co/settings/tokens) with READ permissions.

And then a way to run a final model for interpreting the results.

* [Ollama](https://ollama.com) (local)
* [LM Studio](https://lmstudio.ai) (local)
* [Claude Code](https://claude.com/product/claude-code) (remote)

(Open to adding others if there is an SDK or CLI.)

After installing Homebrew (or running `brew update` if you have it already), you can install all of the other dependencies with:

```bash
brew bundle
```

> [!NOTE]
> **macOS only? Apple silicon only?** For the moment, yes. This implementation takes advantage of Mac-specific tooling which enables hardware-acceleration, namely [VideoToolbox](https://trac.ffmpeg.org/wiki/HWAccelIntro#VideoToolbox) in `ffmpeg`, and [MLX optimizations](https://opensource.apple.com/projects/mlx/) for LLMs and related frameworks.

## Getting started

1. Load your `HF_TOKEN` into your environment.

2. Run `uv sync` to install/load the Python virtual environment.

3. Add your downloaded video file to the root directory of this repository.

4. Kick off the script.

    ```bash
    uv run pipeline.py -i input.mp4
    ```

## Stages

1. First, it will take your input video file and encode an M4A audio file at 192kbps/sec using `ffmpeg`.

2. It will take that M4A audio file and leverage an MLX-optimized LLM based on OpenAI's _Whisper_ model to transcribe the audio content into plain text. Size of this model on-disk is **3.08 GB**. (All LLM-driven transcoding happens locally. It does not push any data to OpenAI or anyone else.)

3. We take the transcription data, and the timestamps, and we go back to `ffmpeg` to extract frames from the video based on the timestamps in the transcription.

4. We want to pause, and review the screengrabs. We want to keep the ones that are the most information-rich and relevant, and throw away everything else. Doing this pruning will help the model work more effectively.

5. At this point, you have usable inputs that you can pass to local or cloud-based model with _Vision_ support.

## What now?

Depending on how much RAM your local system has, you may be able to run models locally.

### Claude Code

If you just want access to large models in the cloud, the `process_with_claude_code.py` script uses Claude Code to produce the documentation from the input artifacts. You need a valid [Anthropic token](https://platform.claude.com/settings/keys).

### Orchestration tooling (local)

* [Ollama](https://ollama.com)
* [LM Studio](https://lmstudio.ai)

Open the desktop app for the tool of your choice.

### Models

The more parameters a model supports, the better the resulting documentation.

* Alibaba Qwen 3.5/3.6 ([LM Studio](https://huggingface.co/Qwen), [Ollama](https://ollama.com/library/qwen3.6))
* Google Gemma 4 ([LM Studio](https://huggingface.co/google), [Ollama](https://ollama.com/library/gemma4))
* [MLX-optimized models](https://huggingface.co/mlx-community) will run best on Apple silicon M-class machines.

### Prompt

See `system_prompt.txt` for the default system prompt.

| Parameter      | Value  |
|----------------|--------|
| Temperature    | `0.2`  |
| Repeat penalty | `1.1`  |
| Top K Sampling | `40`   |
| Top P Sampling | `0.95` |
| Min P Sampling | `0.05` |
