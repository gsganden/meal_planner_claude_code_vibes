# LLM Prompt Library – Model‑Agnostic Management Spec (v0.2)

> **Objective:** Keep *all* prompts and model settings in version control while enabling **zero‑code swaps** between OpenAI, Anthropic, Mistral, or self‑hosted models.

---

## 1. Folder Structure

```
repo_root/
├─ prompts/
│  ├─ extraction/recipe_extract.yaml
│  ├─ chat_actions/substitute.yaml
│  └─ system/chat_system.yaml
├─ llm_registry.yaml          # Maps logical model IDs → provider + params
└─ scripts/prompt_tests.py
```

## 2. LLM Registry (`llm_registry.yaml`)

```yaml
models:
  default:            # logical name used by prompts
    provider: openai
    model: gemini-2.5-flash  # Gemini 2.5 Flash via OpenAI interface
    settings:
      temperature: 0.2
      top_p: 1
  fast:
    provider: openai
    model: gemini-2.5-flash  # Same model for consistency
    settings:
      temperature: 0.4
  fallback:
    provider: openai
    model: gpt-4o
    settings:
      temperature: 0.2
```

*Each **logical id** (`default`, `fast`, `fallback`) is referenced in prompts; swapping means editing this single file.*

## 3. Prompt YAML Schema (`prompt.schema.yaml`)

```yaml
title: "string"                # Human description
author: "email"                # Optional
id: "kebab-case@v1"           # Stable + semver for breaking changes
role: system|user|function
model_ref: default|fast|fallback  # Logical name from registry
schema_ref: recipe_schema.json     # Optional JSON Schema for output
variables:                        # Runtime placeholders
  dish_name: "Name of dish"
content: |
  You are a culinary data extractor...
```

> **No concrete provider/model names** appear inside prompt files.

## 4. Runtime Loading

```python
from promptlib import load_prompt, render, llm_call

prompt = load_prompt("extraction/recipe_extract.yaml")
model_cfg = registry[prompt.model_ref]

messages = render(prompt, dish_name="Pad Thai")
response = llm_call(model_cfg, messages)
```

*`llm_call()` dispatches to provider‑specific wrappers (OpenAI, Anthropic, local vLLM) based on `model_cfg.provider`.*

## 5. CI Validation (`scripts/prompt_tests.py`)

1. **YAML schema** validation (prompt + registry).
2. **Dry‑run** each prompt against a **stub LLM** that echoes JSON to ensure placeholders resolve.
3. **Registry coverage** – error if any `model_ref` missing in `llm_registry.yaml`.

## 6. Environment Overrides

* Set `LLM_REGISTRY_PATH` env var → load alternative registry for staging vs prod.
* Example: staging may map `default` → `gpt-3.5-turbo` to save cost.

## 7. Telemetry & A/B Testing

* Logs include `prompt_id`, `model_ref`, and `provider` for cost attribution.
* Feature flags switch `model_ref` at runtime (e.g., 10 % of `default` traffic → `fast`).

## 8. Prompt Catalogue (MVP)

| ID                  | Purpose                  | model\_ref |
| ------------------- | ------------------------ | ---------- |
| `recipe_extract@v1` | Extract recipe from text | default    |
| `recipe_generate@v1`| Generate recipe from description | default |
| `substitute@v1`     | Ingredient substitutions | fast       |
| `rewrite_step@v1`   | Rewrite instruction      | default    |
| `convert_units@v1`  | Convert units            | default    |
| `scale_recipe@v1`   | Scale servings up/down   | fast       |
| `chat_system@v1`    | System message for chat  | default    |

---

*Now swapping from GPT‑4o to Claude‑3 or a local model is a **one‑line change** in `llm_registry.yaml`, leaving prompt files untouched.*