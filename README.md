# GLM-V

[中文阅读.](./README_zh.md)

<div align="center">
<img src=resources/logo.svg width="40%"/>
</div>
<p align="center">
    👋 Join our <a href="resources/WECHAT.md" target="_blank">WeChat</a> or <a href="https://discord.gg/Hc5z9bx5Xw" target="_blank">Discord</a> communities.
    <br>
    📖 Check out the GLM-5.3-Flash <a href="https://z.ai/blog/glm-5.3-flash" target="_blank">blog</a> and the GLM-4.5V & GLM-4.1V <a href="https://arxiv.org/abs/2507.01006" target="_blank">technical report</a>.
    <br>
    📍 Use the GLM-5.3-Flash API service on the <a href="https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3" target="_blank">API platform</a>.
    <br>
    🔜 Try GLM-5.3-Flash on <a href="https://z.ai" target="_blank">z.ai</a> (coming soon).
</p>

## Introduction

Vision-language models (VLMs) have become a key cornerstone of intelligent systems. As real-world AI tasks grow
increasingly complex, VLMs urgently need to enhance reasoning capabilities beyond basic multimodal perception —
improving accuracy, comprehensiveness, and intelligence — to enable complex problem solving, long-context understanding,
and multimodal agents.

Through our open-source work, we aim to explore the technological frontier together with the community while empowering
more developers to create exciting and innovative applications.

**This open-source repository contains our `GLM-4.6V`, `GLM-4.5V` and `GLM-4.1V` series models.** For performance and
details, see [Model Overview](#model-overview). For known issues,
see [Fixed and Remaining Issues](#fixed-and-remaining-issues).

## Project Updates

- **News**: `2026/09/02`: This repository will no longer be maintained. For questions about GLM-5.3-Flash, please visit the [GLM-5](https://github.com/zai-org/GLM-5) repository for discussion.
- **News**: `2026/08/26`: We released [GLM-5.3-Flash](https://z.ai/blog/glm-5.3-flash), our first open-source natively multimodal model.
- **News**: `2026/04/02`: We released [GLM-5V-Turbo](https://docs.z.ai/guides/vlm/glm-5v-turbo) 
  and [GLM-skills](https://github.com/zai-org/GLM-skills).
- **News**: `2026/03/28`: We have released multiple GLM-V related Skills, covering several specialized areas
  such as GLM-V-Grounding and GLM-V-Prompt-Gen. You are welcome to try them [here](skills).
- **News**: `2025/11/10`: We released **UI2Code^N**, a RL-enhanced UI coding model with UI-to-code, UI-polish, and
  UI-edit capabilities. The model is trained based on `GLM-4.1V-Base`. Check it
  out [here](https://huggingface.co/zai-org/UI2Code_N).
- **News**: `2025/10/27`: We’ve released **Glyph**, a framework for scaling the context length through visual-text
  compression, the glyph model trained based on `GLM-4.1V-Base`. Check it
  out [here](https://huggingface.co/zai-org/Glyph).
- **News**: `2025/08/11`: We released **GLM-4.5V** with significant improvements across multiple benchmarks. We also
  open-sourced our handcrafted **desktop assistant app** for debugging. Once connected to GLM-4.5V, it can capture
  visual information from your PC screen via screenshots or screen recordings. Feel free to try it out or customize it
  into your own multimodal assistant. Click [here](https://huggingface.co/spaces/zai-org/GLM-4.5V-Demo-App) to download
  the installer or [build from source](examples/vllm-chat-helper/README.md)!
- **News**: `2025/07/16`: We have open-sourced the **VLM Reward System** used to train GLM-4.1V-Thinking.View
  the [code repository](glmv_reward) and run locally: `python examples/reward_system_demo.py`.
- **News**: `2025/07/01`: We released **GLM-4.1V-9B-Thinking** and
  its [technical report](https://arxiv.org/abs/2507.01006).

## Model Implementation Code

- GLM-4.5V and GLM-4.6V model algorithm: see the full implementation
  in [transformers](https://github.com/huggingface/transformers/tree/main/src/transformers/models/glm4v_moe).
- GLM-4.1V-9B-Thinking model algorithm: see the full implementation
  in [transformers](https://github.com/huggingface/transformers/tree/main/src/transformers/models/glm4v).
- Both models share identical multimodal preprocessing, but use different conversation templates — please distinguish
  carefully.

## Model Downloads

| Model                | Download Links                                                                                                                                       | Type             |
|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| GLM-4.6V             | [🤗 Hugging Face](https://huggingface.co/zai-org/GLM-4.6V)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/GLM-4.6V)                         | Hybrid Reasoning |
| GLM-4.6V-FP8         | [🤗 Hugging Face](https://huggingface.co/zai-org/GLM-4.6V-FP8)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/GLM-4.6V-FP8)                 | Hybrid Reasoning |
| GLM-4.6V-Flash       | [🤗 Hugging Face](https://huggingface.co/zai-org/GLM-4.6V-Flash)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/GLM-4.6V-Flash)             | Hybrid Reasoning |
| GLM-4.5V             | [🤗 Hugging Face](https://huggingface.co/zai-org/GLM-4.5V)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/GLM-4.5V)                         | Hybrid Reasoning |
| GLM-4.5V-FP8         | [🤗 Hugging Face](https://huggingface.co/zai-org/GLM-4.5V-FP8)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/GLM-4.5V-FP8)                 | Hybrid Reasoning |
| GLM-4.1V-9B-Thinking | [🤗 Hugging Face](https://huggingface.co/zai-org/GLM-4.1V-9B-Thinking)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/GLM-4.1V-9B-Thinking) | Reasoning        |
| GLM-4.1V-9B-Base     | [🤗 Hugging Face](https://huggingface.co/zai-org/GLM-4.1V-9B-Base)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/GLM-4.1V-9B-Base)         | Base             |


+ Hugging Face provides GGUF format model weights. You can download the GGUF format model of GLM-V from [here](https://huggingface.co/collections/ggml-org/glm-v).

## Use Cases

### Grounding

GLM-4.5V / GLM-4.6V / GLM-4.1V have precise grounding capabilities. Given a prompt that requests the location of a specific object, the model
is able to reason step-by-step and identify the bounding boxes of the target object. The query prompt supports
complex descriptions of the target object as well as specified output formats, for example:
>
> - Help me to locate <expr> in the image and give me its bounding boxes.
> - Please pinpoint the bounding box [[x1,y1,x2,y2], …] in the image as per the given description. <expr>

Here, `<expr>` is the description of the target object. The output bounding box is a quadruple $$[x_1,y_1,x_2,y_2]$$
composed of the coordinates of the top-left and bottom-right corners, where each value is normalized by the image
width (for x) or height (for y) and scaled by 1000.

In the response, the special tokens `<|begin_of_box|>` and `<|end_of_box|>` are used to mark the image bounding box in
the answer. The bracket style may vary ([], [[]], (), <>, etc.), but the meaning is the same: to enclose the coordinates
of the box.

### GUI Agent

- `examples/gui-agent`: Demonstrates prompt construction and output handling for GUI Agents, including strategies for
  mobile, PC, and web. Prompt templates differ between GLM-4.1V and GLM-4.5V.

### Quick Demo

- `examples/vlm-helper`: A desktop assistant for GLM multimodal models (mainly GLM-4.5V, compatible with GLM-4.1V),
  supporting text, images, videos, PDFs, PPTs, and more. Connects to the GLM multimodal API for intelligent services
  across scenarios. Download the [installer](https://huggingface.co/spaces/zai-org/GLM-4.5V-Demo-App)
  or [build from source](examples/vlm-helper/README.md).


## Serve GLM-V Series Models Locally

The GLM-V series supports deployment with the following frameworks. Feel free to try them out:

- [SGLang](https://github.com/sgl-project/sglang) (v0.5.15.post1+) — see [cookbook](https://docs.sglang.io/cookbook/autoregressive/GLM/GLM-4.6V)
- [vLLM](https://github.com/vllm-project/vllm) (v0.25.0+) — see [recipes](https://recipes.vllm.ai/zai-org/GLM-4.6V)
- [Transformers](https://github.com/huggingface/transformers) (v0.5.13+) — see [transformers docs](https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/glm4v_moe.md)
- For deployment on the `Ascend NPU` platform, inference frameworks such as xLLM, see [here](examples/Ascend_NPU/README_zh.md).


## Integration with Other Automation Tools

### Midscene.js

[Midscene.js](https://midscenejs.com/en/index.html) is an open-source UI automation SDK driven by vision models, supporting multi-platform automation through JavaScript or Yaml-format process syntax.

Midscene.js has completed integration with GLM-V models. You can quickly experience GLM-V through the [Midscene.js Integration Guide](https://midscenejs.com/model-common-config.html#glm-v).

Here are two examples to help you get started quickly:

- [Call Midscene.js via TypeScript scripts](./examples/midscene-ts-demo)
- [Experience Midscene.js via Yaml scripts](./examples/midscene-yaml-demo)

## Model Fine-tuning

[LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) already supports fine-tuning for GLM-4.5V &
GLM-4.1V-9B-Thinking models. Below is an example of dataset construction using two images. You should organize your
dataset into `finetune.json` in the following format, This is an example for fine-tuning GLM-4.1V-9B.

```json
[
  {
    "messages": [
      {
        "content": "<image>Who are they?",
        "role": "user"
      },
      {
        "content": "<think>\nUser asked me to observe the image and find the answer. I know they are Kane and Goretzka from Bayern Munich.</think>\n<answer>They're Kane and Goretzka from Bayern Munich.</answer>",
        "role": "assistant"
      },
      {
        "content": "<image>What are they doing?",
        "role": "user"
      },
      {
        "content": "<think>\nI need to observe what these people are doing. Oh, they are celebrating on the soccer field.</think>\n<answer>They are celebrating on the soccer field.</answer>",
        "role": "assistant"
      }
    ],
    "images": [
      "mllm_demo_data/1.jpg",
      "mllm_demo_data/2.jpg"
    ]
  }
]
```

1. The content inside `<think> ... </think>` will **not** be stored as conversation history or in fine-tuning data.
2. The `<image>` tag will be replaced with the corresponding image information.
3. For the GLM-4.5V model, the <answer> and </answer> tags should be removed.

Then, you can fine-tune following the standard LLaMA-Factory procedure.

## Model Overview

### GLM-4.6V

GLM-4.6V series model includes two versions: GLM-4.6V (106B), a foundation model designed for cloud and high-performance
cluster scenarios,
and GLM-4.6V-Flash (9B), a lightweight model optimized for local deployment and low-latency applications.
GLM-4.6V scales its context window to 128k tokens in training,
and achieves SoTA performance in visual understanding among models of similar parameter scales.
Crucially, we integrate native Function Calling capabilities for the first time.
This effectively bridges the gap between "visual perception" and "executable action"
providing a unified technical foundation for multimodal agents in real-world business scenarios.

![GLM-4.6V Benchmarks](resources/bench_46v.jpeg)

Beyond achieves SoTA performance across major multimodal benchmarks at comparable model scales. GLM-4.6V introduces
several key features:

- **Native Multimodal Function Calling**
Enables native vision-driven tool use. Images, screenshots, and document pages can be passed directly as tool inputs without text conversion, while visual outputs (charts, search images, rendered pages) are interpreted and integrated into the reasoning chain. This closes the loop from perception to understanding to execution.

- **Interleaved Image-Text Content Generation**
Supports high-quality mixed media creation from complex multimodal inputs. GLM-4.6V takes a multimodal context—spanning documents, user inputs, and tool-retrieved images—and synthesizes coherent, interleaved image-text content tailored to the task. During generation it can actively call search and retrieval tools to gather and curate additional text and visuals, producing rich, visually grounded content.

- **Multimodal Document Understanding**
GLM-4.6V can process up to 128K tokens of multi-document or long-document input, directly interpreting richly formatted pages as images. It understands text, layout, charts, tables, and figures jointly, enabling accurate comprehension of complex, image-heavy documents without requiring prior conversion to plain text.

- **Frontend Replication & Visual Editing**
Reconstructs pixel-accurate HTML/CSS from UI screenshots and supports natural-language-driven edits. It detects layout, components, and styles visually, generates clean code, and applies iterative visual modifications through simple user instructions.

### GLM-4.5V

GLM-4.5V is based on ZhipuAI’s GLM-4.5-Air.
It continues the technical approach of GLM-4.1V-Thinking, achieving SOTA performance among models of the same scale on
42 public vision-language benchmarks.
It covers common tasks such as image, video, and document understanding, as well as GUI agent operations.

Beyond benchmark performance, GLM-4.5V focuses on real-world usability. Through efficient hybrid training, it can handle
diverse types of visual content, enabling full-spectrum vision reasoning, including:

- **Image reasoning** (scene understanding, complex multi-image analysis, spatial recognition)
- **Video understanding** (long video segmentation and event recognition)
- **GUI tasks** (screen reading, icon recognition, desktop operation assistance)
- **Complex chart & long document parsing** (research report analysis, information extraction)
- **Grounding** (precise visual element localization)

The model also introduces a **Thinking Mode** switch, allowing users to balance between quick responses and deep
reasoning. This switch works the same as in the `GLM-4.5` language model.

### GLM-4.1V-9B

Built on the [GLM-4-9B-0414](https://github.com/zai-org/GLM-4) foundation model, the **GLM-4.1V-9B-Thinking** model
introduces a reasoning paradigm and uses RLCS (Reinforcement Learning with Curriculum Sampling) to comprehensively
enhance model capabilities.
It achieves the strongest performance among 10B-level VLMs and matches or surpasses the much larger Qwen-2.5-VL-72B in
18 benchmark tasks.

We also open-sourced the base model **GLM-4.1V-9B-Base** to support researchers in exploring the limits of
vision-language model capabilities.

![rl](resources/rl.jpeg)

Compared with the previous generation CogVLM2 and GLM-4V series, **GLM-4.1V-Thinking** brings:

1. The series’ first reasoning-focused model, excelling in multiple domains beyond mathematics.
2. **64k** context length support.
3. Support for **any aspect ratio** and up to **4k** image resolution.
4. A bilingual (Chinese/English) open-source version.

GLM-4.1V-9B-Thinking integrates the **Chain-of-Thought** reasoning mechanism, improving accuracy, richness, and
interpretability.
It leads on 23 out of 28 benchmark tasks at the 10B parameter scale, and outperforms Qwen-2.5-VL-72B on 18 tasks despite
its smaller size.

## Remaining Issues

Since the open-sourcing of GLM-4.1V, we have received extensive feedback from the community and are well aware that the model still has many shortcomings. In subsequent iterations, we attempted to address several common issues — such as repetitive thinking outputs and formatting errors — which have been mitigated to some extent in this new version.

However, the model still has several limitations and issues that we will fix as soon as possible:

1. Pure text QA capabilities still have significant room for improvement. In this development cycle, our primary focus was on visual multimodal scenarios, and we will enhance pure text abilities in upcoming updates.
2. The model may still overthink or even repeat itself in certain cases, especially when dealing with complex prompts.
3. In some situations, the model may restate the answer again at the end.
4. There remain certain perception limitations, such as counting accuracy and identifying specific individuals, which still require improvement.

Thank you for your patience and understanding. We also welcome feedback and suggestions in the issue section — we will respond and improve as much as we can!

## Citation

If you use this model, please cite the following paper:

```bibtex
@misc{vteam2025glm45vglm41vthinkingversatilemultimodal,
      title={GLM-4.5V and GLM-4.1V-Thinking: Towards Versatile Multimodal Reasoning with Scalable Reinforcement Learning},
      author={V Team and Wenyi Hong and Wenmeng Yu and Xiaotao Gu and Guo Wang and Guobing Gan and Haomiao Tang and Jiale Cheng and Ji Qi and Junhui Ji and Lihang Pan and Shuaiqi Duan and Weihan Wang and Yan Wang and Yean Cheng and Zehai He and Zhe Su and Zhen Yang and Ziyang Pan and Aohan Zeng and Baoxu Wang and Bin Chen and Boyan Shi and Changyu Pang and Chenhui Zhang and Da Yin and Fan Yang and Guoqing Chen and Jiazheng Xu and Jiale Zhu and Jiali Chen and Jing Chen and Jinhao Chen and Jinghao Lin and Jinjiang Wang and Junjie Chen and Leqi Lei and Letian Gong and Leyi Pan and Mingdao Liu and Mingde Xu and Mingzhi Zhang and Qinkai Zheng and Sheng Yang and Shi Zhong and Shiyu Huang and Shuyuan Zhao and Siyan Xue and Shangqin Tu and Shengbiao Meng and Tianshu Zhang and Tianwei Luo and Tianxiang Hao and Tianyu Tong and Wenkai Li and Wei Jia and Xiao Liu and Xiaohan Zhang and Xin Lyu and Xinyue Fan and Xuancheng Huang and Yanling Wang and Yadong Xue and Yanfeng Wang and Yanzi Wang and Yifan An and Yifan Du and Yiming Shi and Yiheng Huang and Yilin Niu and Yuan Wang and Yuanchang Yue and Yuchen Li and Yutao Zhang and Yuting Wang and Yu Wang and Yuxuan Zhang and Zhao Xue and Zhenyu Hou and Zhengxiao Du and Zihan Wang and Peng Zhang and Debing Liu and Bin Xu and Juanzi Li and Minlie Huang and Yuxiao Dong and Jie Tang},
      year={2025},
      eprint={2507.01006},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2507.01006},
}
```
