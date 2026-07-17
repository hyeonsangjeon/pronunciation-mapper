# Pronunciation Mapper V2

[![PyPI](https://img.shields.io/pypi/v/pronunciation-mapper)](https://pypi.org/project/pronunciation-mapper/)
[![Python](https://img.shields.io/pypi/pyversions/pronunciation-mapper)](https://pypi.org/project/pronunciation-mapper/)
[![CI](https://github.com/hyeonsangjeon/pronunciation-mapper/actions/workflows/ci.yml/badge.svg)](https://github.com/hyeonsangjeon/pronunciation-mapper/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/pypi/dm/pronunciation-mapper?label=downloads%2Fmonth)](https://pypistats.org/packages/pronunciation-mapper)
[![License](https://img.shields.io/pypi/l/pronunciation-mapper)](https://github.com/hyeonsangjeon/pronunciation-mapper/blob/main/LICENSE)

[한국어](https://github.com/hyeonsangjeon/pronunciation-mapper/blob/main/README.md) · [Usage guide](https://hyeonsangjeon.github.io/pronunciation-mapper/) · [PyPI](https://pypi.org/project/pronunciation-mapper/)

Pronunciation Mapper V2 rewrites Korean ASR output into canonical database terms for lexical and hybrid search.

It uses a bounded hybrid pipeline:

1. deterministic number, alias, Jamo, and edit-distance retrieval;
2. a Microsoft Foundry decision agent by default, or Ollama locally;
3. strict validation that only locally retrieved candidate IDs and `db_terms` can be applied;
4. deterministic fallback on provider failure.

OpenAI and Claude are reference-only providers in V2. The `openai` Python package included by the Foundry extra is only the Azure-compatible Responses transport returned by `AIProjectClient`; it does not require an OpenAI token.

The downloads badge uses the PSF-hosted [pypistats](https://pypistats.org/) monthly aggregate. It excludes known mirrors and refreshes daily; a new package may show an indexing state before its first daily aggregate.

## Install

For the deterministic mapper and CLI:

```bash
python -m pip install pronunciation-mapper
```

Microsoft Foundry (default V2 provider):

```bash
python -m pip install 'pronunciation-mapper[foundry]'
az login
export FOUNDRY_PROJECT_ENDPOINT='https://<account>.services.ai.azure.com/api/projects/<project>'
export FOUNDRY_MODEL='<deployment-name>'
```

Optional Ollama:

```bash
python -m pip install 'pronunciation-mapper[ollama]'
ollama pull qwen3.5:4b
export OLLAMA_MODEL='qwen3.5:4b'
```

For repository development and the full test suite, install from a source checkout:

```bash
python -m pip install -e '.[dev,foundry,ollama]'
```

## Use

Deterministic local rewriting requires no network credentials:

```python
from pronunciation_mapper import PronunciationMapper

mapper = PronunciationMapper(["customer", "server"])
query = "커스터머 서버에서 조회"
result = mapper.map_sentence(query)

print(f"Input: {query}")
print(f"Output: {result}")
```

```text
Input: 커스터머 서버에서 조회
Output: customer server에서 조회
```

Microsoft Foundry is the default V2 decision provider:

```python
from pronunciation_mapper import AgenticPronunciationMapper

with AgenticPronunciationMapper(
    ["XPN36", "account_no", "transaction", "server", "log"],
    custom_mappings={
        "엑스피엔36": "XPN36",
        "서버": "server",
        "로그": "log",
    },
) as mapper:
    query = "엑스피엔36 서버에서 트랜잭숑 로그"
    result = mapper.rewrite_sync(query)

    print(f"Input: {query}")
    print(f"Output: {result.rewritten_text}")
    print(f"Provider: {result.provider}")
```

Example output:

```text
Input: 엑스피엔36 서버에서 트랜잭숑 로그
Output: XPN36 server에서 transaction log
Provider: azure-foundry
```

Exact aliases are applied locally. Ambiguous phonetic candidates are selected by the configured provider, so confidence, latency, usage, and `keep`/`abstain` decisions may vary. Use `result.to_dict()` when you need the full decision trace.

Factory-created providers are closed by the mapper context manager. Injected custom providers and clients remain caller-owned. Defaults bound untrusted work to 4,096 input characters, 64 lexical spans, and 256 characters per token. Foundry requests use a 30-second timeout, one retry, and a 2,048-token output cap. Ollama requests use a 30-second timeout, disable thinking mode, and cap output at 2,048 tokens. Each limit is configurable.

Korean number normalization is intentionally conservative. Explicit units/counters and long spoken identifiers are normalized, while ambiguous ordinary expressions such as `일일이` and `천만 다행` are preserved.

The original `PronunciationMapper` class and CLI commands remain available and never require network credentials.

See the [documentation index](https://github.com/hyeonsangjeon/pronunciation-mapper/blob/main/docs/README.md), [changelog](https://github.com/hyeonsangjeon/pronunciation-mapper/blob/main/CHANGELOG.md), [V2 architecture document](https://github.com/hyeonsangjeon/pronunciation-mapper/blob/main/docs/V2_ARCHITECTURE.md), [V2.0.1 release record](https://github.com/hyeonsangjeon/pronunciation-mapper/blob/main/docs/releases/v2.0.1.md), the [GitHub Actions and external-tenant Foundry OIDC setup](https://github.com/hyeonsangjeon/pronunciation-mapper/blob/main/docs/CI_SETUP.md), and the full Korean [README](https://github.com/hyeonsangjeon/pronunciation-mapper/blob/main/README.md).
